FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies if needed
RUN yum install -y gcc gcc-c++ make

# Copy and install Python dependencies (cache bust)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt --force-reinstall

# Copy application files
COPY service-account.json ${LAMBDA_TASK_ROOT}
COPY lambda_function.py ${LAMBDA_TASK_ROOT}
COPY prompt_certificate_type.txt ${LAMBDA_TASK_ROOT}
COPY prompt_earthquake_insurance.txt ${LAMBDA_TASK_ROOT}
COPY prompt_life_insurance.txt ${LAMBDA_TASK_ROOT}
COPY prompt_small_mutual_aid.txt ${LAMBDA_TASK_ROOT}
COPY prompt_social_insurance.txt ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"]
