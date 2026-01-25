import json
import boto3
import os
from datetime import datetime
from typing import List, Dict, Any
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Initialize AWS clients
s3 = boto3.client('s3')
sqs = boto3.client('sqs')
workmail = boto3.client('workmail')

# Environment variables
EMAIL_QUEUE_URL = os.environ.get('EMAIL_QUEUE_URL')
EMAIL_BUCKET = os.environ.get('EMAIL_BUCKET')
DELETE_CATEGORIES = os.environ.get('DELETE_CATEGORIES', 'spam,promotional,low-priority').split(',')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '50'))
MODEL_PATH = os.environ.get('MODEL_PATH', '/tmp/model')

# Global model variables (loaded once per container)
tokenizer = None
model = None

# Category mapping
CATEGORY_MAP = {
    0: 'spam',
    1: 'promotional',
    2: 'work',
    3: 'personal',
    4: 'low-priority',
    5: 'high-priority',
    6: 'newsletter'
}


def load_model():
    """Load pre-trained BERT model (runs once per container)."""
    global tokenizer, model
    
    if model is None:
        print("Loading BERT model...")
        
        # Download model from S3 if not in /tmp
        if not os.path.exists(MODEL_PATH):
            os.makedirs(MODEL_PATH, exist_ok=True)
            
            # Download fine-tuned model from S3
            model_bucket = os.environ.get('MODEL_BUCKET', EMAIL_BUCKET)
            
            for file in ['config.json', 'pytorch_model.bin', 'tokenizer_config.json', 'vocab.txt']:
                s3.download_file(
                    model_bucket,
                    f'models/email-classifier/{file}',
                    f'{MODEL_PATH}/{file}'
                )
        
        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
        model.eval()  # Set to evaluation mode
        
        print("Model loaded successfully")


def lambda_handler(event, context):
    """
    Batch process queued emails during off-peak hours.
    Triggered by EventBridge schedule (e.g., every 2 hours).
    """
    try:
        load_model()
        
        # Receive messages from SQS in batch
        messages = receive_batch_messages()
        
        if not messages:
            print("No messages in queue")
            return {
                'statusCode': 200,
                'body': json.dumps({'processed': 0, 'message': 'No emails to process'})
            }
        
        print(f"Processing {len(messages)} emails in batch")
        
        # Load email data from S3
        emails = []
        for msg in messages:
            body = json.loads(msg['Body'])
            email_data = load_email_from_s3(body['s3Key'])
            emails.append({
                'messageId': body['messageId'],
                's3Key': body['s3Key'],
                'data': email_data,
                'receiptHandle': msg['ReceiptHandle']
            })
        
        # Batch classify all emails
        categories = batch_classify_emails(emails)
        
        # Process results
        deleted_count = 0
        retained_count = 0
        
        for email_info, category in zip(emails, categories):
            message_id = email_info['messageId']
            
            if should_delete_email(category):
                # Archive to S3 before deletion
                archive_email(email_info, category)
                
                # Mark for deletion in WorkMail
                # Note: Actual deletion handled separately
                mark_for_deletion(message_id, category)
                deleted_count += 1
            else:
                # Move to processed folder
                move_to_processed(email_info, category)
                retained_count += 1
            
            # Delete from queue
            sqs.delete_message(
                QueueUrl=EMAIL_QUEUE_URL,
                ReceiptHandle=email_info['receiptHandle']
            )
        
        result = {
            'processed': len(emails),
            'deleted': deleted_count,
            'retained': retained_count,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        print(f"Batch processing complete: {json.dumps(result)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
            
    except Exception as e:
        print(f"Error in batch processing: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def receive_batch_messages() -> List[Dict]:
    """Receive batch of messages from SQS."""
    try:
        response = sqs.receive_message(
            QueueUrl=EMAIL_QUEUE_URL,
            MaxNumberOfMessages=BATCH_SIZE,
            WaitTimeSeconds=5,
            MessageAttributeNames=['All']
        )
        return response.get('Messages', [])
    except Exception as e:
        print(f"Error receiving messages: {str(e)}")
        return []


def load_email_from_s3(s3_key: str) -> Dict:
    """Load email data from S3."""
    try:
        response = s3.get_object(Bucket=EMAIL_BUCKET, Key=s3_key)
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"Error loading email from S3: {str(e)}")
        raise


def batch_classify_emails(emails: List[Dict]) -> List[str]:
    """
    Classify multiple emails in a single batch for efficiency.
    Uses pre-trained BERT model.
    """
    try:
        # Prepare texts for batch processing
        texts = []
        for email_info in emails:
            data = email_info['data']
            text = f"Subject: {data['subject']}\n\nFrom: {data['sender']}\n\n{data['body']}"
            texts.append(text[:512])  # BERT max length
        
        # Tokenize in batch
        inputs = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors='pt'
        )
        
        # Run inference
        with torch.no_grad():
            outputs = model(**inputs)
            predictions = torch.argmax(outputs.logits, dim=1)
        
        # Map predictions to categories
        categories = [CATEGORY_MAP[pred.item()] for pred in predictions]
        
        return categories
        
    except Exception as e:
        print(f"Error in batch classification: {str(e)}")
        # Return default category on error
        return ['uncategorized'] * len(emails)


def should_delete_email(category: str) -> bool:
    """Determine if email should be deleted based on category."""
    return category in DELETE_CATEGORIES


def archive_email(email_info: Dict, category: str) -> None:
    """Archive email before deletion for compliance."""
    try:
        archive_key = f"archive/{category}/{datetime.utcnow().strftime('%Y/%m/%d')}/{email_info['messageId']}.json"
        
        # Copy to archive
        s3.copy_object(
            Bucket=EMAIL_BUCKET,
            CopySource={'Bucket': EMAIL_BUCKET, 'Key': email_info['s3Key']},
            Key=archive_key
        )
        
        # Add metadata
        s3.put_object_tagging(
            Bucket=EMAIL_BUCKET,
            Key=archive_key,
            Tagging={
                'TagSet': [
                    {'Key': 'category', 'Value': category},
                    {'Key': 'deletedAt', 'Value': datetime.utcnow().isoformat()}
                ]
            }
        )
        
    except Exception as e:
        print(f"Error archiving email: {str(e)}")


def mark_for_deletion(message_id: str, category: str) -> None:
    """
    Mark email for deletion in WorkMail.
    Note: WorkMail doesn't have direct delete API.
    This creates a record for manual cleanup or IMAP-based deletion.
    """
    try:
        deletion_key = f"deletions/{datetime.utcnow().strftime('%Y/%m/%d')}/{message_id}.json"
        
        s3.put_object(
            Bucket=EMAIL_BUCKET,
            Key=deletion_key,
            Body=json.dumps({
                'messageId': message_id,
                'category': category,
                'markedAt': datetime.utcnow().isoformat()
            }),
            ContentType='application/json'
        )
        
    except Exception as e:
        print(f"Error marking email for deletion: {str(e)}")


def move_to_processed(email_info: Dict, category: str) -> None:
    """Move email to processed folder."""
    try:
        processed_key = f"processed/{category}/{datetime.utcnow().strftime('%Y/%m/%d')}/{email_info['messageId']}.json"
        
        # Copy to processed folder
        s3.copy_object(
            Bucket=EMAIL_BUCKET,
            CopySource={'Bucket': EMAIL_BUCKET, 'Key': email_info['s3Key']},
            Key=processed_key
        )
        
        # Delete from pending
        s3.delete_object(
            Bucket=EMAIL_BUCKET,
            Key=email_info['s3Key']
        )
        
    except Exception as e:
        print(f"Error moving email to processed: {str(e)}")
