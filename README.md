# Telegram Text Recognition Bot

This is a Telegram bot that extracts text from images provided by the user. It uses AWS Textract to extract data when the user uploads images. The images are stored in an S3 bucket, and AWS Textract retrieves the images from S3 to extract and return the text.

## Services Used
- **AWS S3**: To store the uploaded images.
- **AWS Textract**: To extract text from the images.
- **Telegram Bot**: To interact with users and receive images.

## Setup Instructions
1. Install the required libraries by running `pip install -r requirements.txt` in your terminal.
2. Create an AWS account and set up an S3 bucket to store the images.
3. Create an AWS Textract account and set up the necessary permissions to access the S3 bucket
4. Create a Telegram bot using the BotFather bot and get the bot token.

### Prerequisites
1. **AWS CLI**: Install and configure the AWS CLI on your machine.
2. **Python**: Ensure Python is installed on your machine.
3. **Telegram Bot**: Create a Telegram bot using BotFather and obtain the API token.
4. **S3 Bucket**: Create an S3 bucket in your AWS account.

### Configuration
1. **AWS CLI Configuration**:
   ```sh
   aws configure