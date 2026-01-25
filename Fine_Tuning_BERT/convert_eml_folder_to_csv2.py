#!/usr/bin/env python3
"""
Convert .eml files to CSV for manual labeling
Creates a CSV with email content and empty category column
You can then open the CSV and add categories manually
"""

import email
import csv
import os
from email import policy

def parse_eml_file(filepath):
    """Extract subject, sender, and body from .eml file"""
    try:
        with open(filepath, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
        
        subject = msg.get('subject', '')
        sender = msg.get('from', '')
        date = msg.get('date', '')
        
        # Get email body - try multiple methods
        body = ''
        html_body = ''
        
        if msg.is_multipart():
            # Walk through all parts
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                # Get plain text
                if content_type == 'text/plain' and not body:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                    except Exception as e:
                        print(f"  Warning: Could not decode text/plain in {os.path.basename(filepath)}: {e}")
                
                # Get HTML as backup
                elif content_type == 'text/html' and not html_body:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_body = payload.decode('utf-8', errors='ignore')
                    except Exception as e:
                        print(f"  Warning: Could not decode text/html in {os.path.basename(filepath)}: {e}")
        else:
            # Not multipart - get payload directly
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    content_type = msg.get_content_type()
                    if content_type == 'text/plain':
                        body = payload.decode('utf-8', errors='ignore')
                    elif content_type == 'text/html':
                        html_body = payload.decode('utf-8', errors='ignore')
                    else:
                        # Try to decode as text anyway
                        body = payload.decode('utf-8', errors='ignore')
            except Exception as e:
                # Last resort - get as string
                try:
                    body = str(msg.get_payload())
                except:
                    body = ''
        
        # Use plain text if available, otherwise use HTML
        if not body and html_body:
            # Simple HTML stripping (remove tags)
            import re
            body = re.sub('<[^<]+?>', '', html_body)
            body = re.sub(r'\s+', ' ', body)  # Clean up whitespace
        
        # Clean up body
        body = body.strip()
        
        # Combine into training format
        text = f"Subject: {subject}\n\nFrom: {sender}\n\n{body[:1000]}"  # Limit body length
        
        # Debug: Show if body is empty
        if not body:
            print(f"  ⚠️  No body found in {os.path.basename(filepath)}")
        
        return {
            'filename': os.path.basename(filepath),
            'subject': subject,
            'sender': sender,
            'date': date,
            'text': text,
            'body_preview': body[:200],  # First 200 chars for verification
            'category': ''  # Empty - you'll fill this in manually
        }
    
    except Exception as e:
        print(f"❌ Error parsing {filepath}: {e}")
        return None

def convert_eml_folder_to_csv(eml_folder='workmail_exports', output_csv='emails_to_label.csv'):
    """
    Convert all .eml files in a folder to CSV
    Creates CSV with empty category column for manual labeling
    """
    
    if not os.path.exists(eml_folder):
        print(f"Error: Folder '{eml_folder}' not found!")
        print(f"Please create the folder and add your .eml files")
        return
    
    # Find all .eml files
    eml_files = [f for f in os.listdir(eml_folder) if f.endswith('.eml')]
    
    if not eml_files:
        print(f"No .eml files found in '{eml_folder}' folder")
        return
    
    print(f"Found {len(eml_files)} .eml files")
    print("Converting to CSV...\n")
    
    # Convert to CSV
    emails_data = []
    
    for filename in eml_files:
        filepath = os.path.join(eml_folder, filename)
        email_data = parse_eml_file(filepath)
        
        if email_data:
            emails_data.append(email_data)
            print(f"✓ Processed: {filename}")
    
    # Write to CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['filename', 'subject', 'sender', 'date', 'body_preview', 'text', 'category']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(emails_data)
    
    print(f"\n{'='*60}")
    print(f"✅ SUCCESS! Created {output_csv}")
    print(f"{'='*60}")
    print(f"\nProcessed {len(emails_data)} emails")
    print(f"\nNext steps:")
    print(f"1. Open {output_csv} in Excel or Google Sheets")
    print(f"2. Fill in the 'category' column for each email")
    print(f"   Categories: spam, promotional, work, personal, low-priority, high-priority, newsletter")
    print(f"3. Save the file")
    print(f"4. Run: python prepare_training_data.py")
    print(f"\nExample categories:")
    print(f"  - spam: Unsolicited emails")
    print(f"  - promotional: Marketing emails")
    print(f"  - work: Work-related emails")
    print(f"  - personal: Personal emails")
    print(f"  - low-priority: Automated notifications")
    print(f"  - high-priority: Urgent emails")
    print(f"  - newsletter: Subscribed newsletters")

if __name__ == '__main__':
    # Configuration
    EML_FOLDER = 'workmail_exports'  # Folder containing your .eml files
    OUTPUT_CSV = 'emails_to_label.csv'  # Output CSV file
    
    print("="*60)
    print("EML to CSV Converter")
    print("="*60)
    print(f"Looking for .eml files in: {EML_FOLDER}/")
    print(f"Will create: {OUTPUT_CSV}")
    print()
    
    # Convert
    convert_eml_folder_to_csv(EML_FOLDER, OUTPUT_CSV)