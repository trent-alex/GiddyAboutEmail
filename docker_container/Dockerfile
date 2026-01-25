# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.11

# Install build tools for numpy
RUN yum install -y gcc gcc-c++ && yum clean all

# Copy requirements
COPY requirements_batch.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --only-binary :all: -r requirements_batch.txt --target "${LAMBDA_TASK_ROOT}"

# Copy Lambda function
COPY lambda_batch_processor.py ${LAMBDA_TASK_ROOT}

# Set handler
CMD [ "lambda_batch_processor.lambda_handler" ]
