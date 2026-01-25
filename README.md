<p align="center"><img src="images/Giddy_header.png" alt="Project Banner" width="800"></p>
# Giddy About Email </br>
Welcome, This is my project to automate the emails I receive from AWS workmail.  

I started a small business, PivotalLift LLC.  I registered it with SBA, SAM.gov, and grants.gov.  I also use it for aviation sites. The problem is it now getting alot of junk mail.  I dont want to spend time reading each one, but also I want to be responsive to clients or leads.

## Objectives

1. **Email Management** My LLC is receiving too many random emails, I want an automation to eliminate the unwanted sales so I only have to focus on the important ones.  
2. **Learn ~AWS Sagemaker~ PyTorch and LLM employment** I plan to LLM NLP vice flow control on key words. Maybe even do a comparison. Sagemaker endpoint is too expensive.  I'll just build my own via pytorch and upload it.
3. **Keep my AWS costs low** self explanatory
4. **Display dashboard on Github**  why not?

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
   - single blob
   
2. **SQS**
   - FiFO queue
   - Dead letter queue

3. **Queue Lambda** (256MB, <2s)
   - because serverless keeps conts down
   - Stores emails in S3
  

4. **Batch Processor Lambda** (3GB, ~120s)
   - Loads DistilBERT model
   - Processes 50 emails at once

5. **Elastic Container Registry**
  
## Current Process
:cloud: 

**:white_check_mark: S3 Storage** <br>
Completed through console pretty easy

**:white_check_mark: SQS**<br>
Completed both queues through console

**:white_check_mark: Queue Lambda**<br>
Completed through console

:computer: In local Terminal mix of Powershell and Bash
Take note I did all the docker from a MAC (Note: CRLF versus LF) While WSL has improved Docker and like containerization seems to work better for MacOS, Linux and the like

**:white_check_mark: Train Bert Model**<br>
Drafted python script to capture my emails
  
**:white_check_mark: Batch Lambda**<br> 
I used Docker desktop to build the image.
The requirements.txt file had to be tagged to specific version as pytorch and transformers complained if not.

**[] Testing Lambda**

