# Giddy About Email
Welcome, This is my project to automate the emails I receive from AWS workmail.  

I started a small business, PivotalLift LLC.  I registered it with SBA, SAM.gov, and grants.gov.  I also use it for aviation sites. The problem is it now getting alot of junk mail.  I dont want to spend time reading each one, but also I want to be responsive to clients or leads.

## Objectives

1. **Email Management** My LLC is receiving too many random emails, I want an automation to eliminate the unwanted sales so I only have to focus 
2. **Learn ~AWS Sagemaker~ PyTorch and LLM employment** Yeah, use LLM NLP vice flow control. Maybe even do comparison. Sagemaker endpoint is too expensive.  I just build my own in upload it.
3. **Keep my AWS costs low** self explanatory
4. ** Display dashboard on Github**  why not?

## Cloud Architecture
```
WorkMail → Queue Lambda → SQS → S3
                                  ↓
EventBridge (schedule) → Batch Lambda + BERT → Categorize & Delete
                                                          ↓
                                               S3 Archive (compliance)
```
## Components

1. **S3 Storage**
   - single container
   
2. **SQS**
   - FiFO queue
   - Dead letter queue

3. **Queue Lambda** (256MB, <2s)
   - Lightweight, fast response
   - Stores emails in S3
  

4.**Batch Processor Lambda** (3GB, ~120s)
   - Loads DistilBERT model
   - Processes 50 emails at once
  
## Current Process
On cloud :cloud:---------------------------------
**✅ S3 Storage** 
Completed through console pretty easy

**✅ SQS**
Completed both queues through console

**✅ Queue Lambda**
Completed through console

In local Terminal :computer:--------------------
**✅ Train Bert Model**
Drafted python script to capture my emails
  
**[ ] Batch Lambda** 
Currently the model exceeds the 250 MB limit for zip file to lambda. It sits at 468 with just to transformer and the pytorch cpu libraries.
Creating a docker container which has a 10GB limit 