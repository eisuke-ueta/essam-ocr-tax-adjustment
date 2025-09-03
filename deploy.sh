#!/bin/bash
set -e

# Configuration
REGION="ap-northeast-1"
PROFILE="jinbay-dev"
ECR_REPOSITORY="essam-ocr-tax-adjustment"
FUNCTION_NAME="essam-ocr-tax-adjustment"
IMAGE_TAG="latest"

# Check command line arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "📖 AWS Lambda Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --status    Check Lambda function status only"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Required Environment Variables:"
    echo "  VERTEX_AI_PROJECT_ID         Google Cloud Project ID for Vertex AI"
    echo "  API_KEY                      Bearer token for API authentication"
    echo "  GOOGLE_APPLICATION_CREDENTIALS  Path to Google Cloud service account key file"
    echo "  VERTEX_AI_LOCATION           Vertex AI region (default: asia-northeast1)"
    echo ""
    echo "Examples:"
    echo "  export VERTEX_AI_PROJECT_ID=\"your-gcp-project\""
    echo "  export API_KEY=\"your-secret-token\""
    echo "  export GOOGLE_APPLICATION_CREDENTIALS=\"/path/to/service-account.json\""
    echo "  export VERTEX_AI_LOCATION=\"asia-northeast1\"  # optional"
    echo "  $0              Full deployment (build, push, update)"
    echo "  $0 --status     Check function status"
    echo ""
    exit 0
fi

if [ "$1" = "--status" ] || [ "$1" = "-s" ]; then
    echo "🔍 Checking Lambda function status only..."
    
    # Function to check Lambda function status and display details
    check_lambda_status() {
        local function_name=$1
        
        echo "🔍 Checking Lambda function status..."
        
        # Check if function exists
        if ! aws lambda get-function --function-name $function_name --region $REGION --profile $PROFILE > /dev/null 2>&1; then
            echo "❌ Function '$function_name' not found"
            return 1
        fi
        
        # Get function details
        echo "📋 Function Details:"
        aws lambda get-function --function-name $function_name --region $REGION --profile $PROFILE \
            --query '{
                State: Configuration.State,
                StateReason: Configuration.StateReason,
                LastUpdateStatus: Configuration.LastUpdateStatus,
                LastUpdateStatusReason: Configuration.LastUpdateStatusReason,
                LastModified: Configuration.LastModified,
                Runtime: Configuration.Runtime,
                MemorySize: Configuration.MemorySize,
                Timeout: Configuration.Timeout
            }' --output table
        
        # Check if function is ready for updates
        local state=$(aws lambda get-function --function-name $function_name --region $REGION --profile $PROFILE --query 'Configuration.State' --output text)
        local last_update_status=$(aws lambda get-function --function-name $function_name --region $REGION --profile $PROFILE --query 'Configuration.LastUpdateStatus' --output text)
        
        echo ""
        if [ "$state" = "Active" ] && [ "$last_update_status" = "Successful" ]; then
            echo "✅ Function is ready for updates"
            return 0
        elif [ "$last_update_status" = "InProgress" ]; then
            echo "⏳ Function update is currently in progress. Please wait and try again later."
            echo "💡 You can run this script again to check the status."
            return 1
        elif [ "$last_update_status" = "Failed" ]; then
            echo "❌ Last update failed. Check the StateReason above for details."
            return 1
        else
            echo "⚠️  Function is in state: $state, Last update status: $last_update_status"
            echo "💡 You may need to wait before attempting updates."
            return 1
        fi
    }
    
    check_lambda_status $FUNCTION_NAME
    exit $?
fi

echo "🚀 Starting deployment of essam-ocr-tax-adjustment Lambda function..."

# Check for required environment variables
echo "📋 Checking required environment variables..."
if [ -z "$VERTEX_AI_PROJECT_ID" ]; then
    echo "❌ VERTEX_AI_PROJECT_ID environment variable is required"
    echo "   Set it with: export VERTEX_AI_PROJECT_ID=\"your-gcp-project-id\""
    exit 1
fi

if [ -z "$API_KEY" ]; then
    echo "❌ API_KEY environment variable is required"
    echo "   Set it with: export API_KEY=\"your-bearer-token\""
    exit 1
fi

if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "❌ GOOGLE_APPLICATION_CREDENTIALS environment variable is required"
    echo "   Set it with: export GOOGLE_APPLICATION_CREDENTIALS=\"/path/to/service-account.json\""
    exit 1
fi

echo "✅ Required environment variables found:"
echo "   VERTEX_AI_PROJECT_ID: $VERTEX_AI_PROJECT_ID"
echo "   VERTEX_AI_LOCATION: ${VERTEX_AI_LOCATION:-asia-northeast1}"
echo "   GOOGLE_APPLICATION_CREDENTIALS: $GOOGLE_APPLICATION_CREDENTIALS"
echo "   API_KEY: [HIDDEN]"

# Step 1: Check if logged in to AWS
echo "📋 Step 1: Checking AWS authentication..."
if ! aws sts get-caller-identity --profile $PROFILE > /dev/null 2>&1; then
    echo "❌ Not authenticated. Please login first:"
    echo "aws sso login --profile $PROFILE --use-device-code"
    exit 1
fi

echo "✅ AWS authentication verified"

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --profile $PROFILE --query Account --output text)
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
REPOSITORY_URI="$ECR_URI/$ECR_REPOSITORY"

echo "📋 Account ID: $ACCOUNT_ID"
echo "📋 ECR Repository URI: $REPOSITORY_URI"

# Step 2: Create ECR repository if it doesn't exist
echo "📋 Step 2: Creating ECR repository if needed..."
if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $REGION --profile $PROFILE > /dev/null 2>&1; then
    echo "Creating ECR repository: $ECR_REPOSITORY"
    aws ecr create-repository \
        --repository-name $ECR_REPOSITORY \
        --region $REGION \
        --profile $PROFILE
    echo "✅ ECR repository created"
else
    echo "✅ ECR repository already exists"
fi

# Step 3: Login to ECR
echo "📋 Step 3: Logging into ECR..."
aws ecr get-login-password --region $REGION --profile $PROFILE | \
    docker login --username AWS --password-stdin $ECR_URI
echo "✅ ECR login successful"

# Step 4: Build Docker image
echo "📋 Step 4: Building Docker image..."
docker build --platform linux/amd64 -t $ECR_REPOSITORY:$IMAGE_TAG .
echo "✅ Docker image built successfully"

# Step 5: Tag and push image
echo "📋 Step 5: Tagging and pushing image to ECR..."
docker tag $ECR_REPOSITORY:$IMAGE_TAG $REPOSITORY_URI:$IMAGE_TAG
docker push $REPOSITORY_URI:$IMAGE_TAG
echo "✅ Image pushed to ECR successfully"

# Step 6: Create or update Lambda function
echo "📋 Step 6: Creating/updating Lambda function..."

# Function to check Lambda function status and display details
check_lambda_status() {
    local function_name=$1
    
    echo "🔍 Checking Lambda function status..."
    
    # Check if function exists
    if ! aws lambda get-function --function-name $function_name --region $REGION --profile $PROFILE > /dev/null 2>&1; then
        echo "❌ Function '$function_name' not found"
        return 1
    fi
    
    # Get function details
    echo "📋 Function Details:"
    aws lambda get-function --function-name $function_name --region $REGION --profile $PROFILE \
        --query '{
            State: Configuration.State,
            StateReason: Configuration.StateReason,
            LastUpdateStatus: Configuration.LastUpdateStatus,
            LastUpdateStatusReason: Configuration.LastUpdateStatusReason,
            LastModified: Configuration.LastModified,
            Runtime: Configuration.Runtime,
            MemorySize: Configuration.MemorySize,
            Timeout: Configuration.Timeout
        }' --output table
    
    # Check if function is ready for updates
    local state=$(aws lambda get-function --function-name $function_name --region $REGION --profile $PROFILE --query 'Configuration.State' --output text)
    local last_update_status=$(aws lambda get-function --function-name $function_name --region $REGION --profile $PROFILE --query 'Configuration.LastUpdateStatus' --output text)
    
    echo ""
    if [ "$state" = "Active" ] && [ "$last_update_status" = "Successful" ]; then
        echo "✅ Function is ready for updates"
        return 0
    elif [ "$last_update_status" = "InProgress" ]; then
        echo "⏳ Function update is currently in progress"
        return 2
    elif [ "$last_update_status" = "Failed" ]; then
        echo "❌ Last update failed"
        return 1
    else
        echo "⚠️  Function is in state: $state, Last update status: $last_update_status"
        return 2
    fi
}

# Function to wait for Lambda function to be ready
wait_for_function_ready() {
    local function_name=$1
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for function to be ready..."
    while [ $attempt -le $max_attempts ]; do
        local state=$(aws lambda get-function --function-name $function_name --region $REGION --profile $PROFILE --query 'Configuration.State' --output text 2>/dev/null)
        local last_update_status=$(aws lambda get-function --function-name $function_name --region $REGION --profile $PROFILE --query 'Configuration.LastUpdateStatus' --output text 2>/dev/null)
        
        if [ "$state" = "Active" ] && [ "$last_update_status" = "Successful" ]; then
            echo "✅ Function is ready"
            return 0
        elif [ "$last_update_status" = "Failed" ]; then
            echo "❌ Last update failed"
            return 1
        fi
        
        echo "Function state: $state, Last update status: $last_update_status (attempt $attempt/$max_attempts)"
        sleep 10
        attempt=$((attempt + 1))
    done
    
    echo "❌ Timeout waiting for function to be ready"
    return 1
}

# Function to update Lambda with retry logic
update_lambda_with_retry() {
    local update_type=$1
    local aws_command=$2
    local max_retries=5
    local retry_delay=30
    local attempt=1
    
    while [ $attempt -le $max_retries ]; do
        echo "Attempt $attempt/$max_retries: $update_type"
        
        if eval "$aws_command"; then
            echo "✅ $update_type completed successfully"
            return 0
        else
            local exit_code=$?
            echo "❌ $update_type failed (exit code: $exit_code)"
            
            # Check if it's a ResourceConflictException or similar recoverable error
            if [ $exit_code -eq 254 ] || [ $exit_code -eq 255 ] || [ $exit_code -eq 1 ]; then
                if [ $attempt -lt $max_retries ]; then
                    echo "⏳ Waiting ${retry_delay}s before retry..."
                    sleep $retry_delay
                    attempt=$((attempt + 1))
                else
                    echo "❌ Max retries reached for $update_type"
                    return 1
                fi
            else
                echo "❌ Non-recoverable error for $update_type"
                return 1
            fi
        fi
    done
}

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --profile $PROFILE > /dev/null 2>&1; then
    echo "Updating existing Lambda function..."
    
    # Check initial function status
    check_lambda_status $FUNCTION_NAME
    status_result=$?
    
    if [ $status_result -eq 2 ]; then
        echo "⏳ Function is not ready. Waiting for current operation to complete..."
        if ! wait_for_function_ready $FUNCTION_NAME; then
            echo "❌ Function is not ready for updates. Please try again later."
            exit 1
        fi
    elif [ $status_result -eq 1 ]; then
        echo "❌ Function is in a failed state. Please check the function manually."
        exit 1
    fi
    
    # Update function code with retry logic
    echo "🔄 Updating function code..."
    update_lambda_with_retry "Updating function code" \
        "aws lambda update-function-code --function-name $FUNCTION_NAME --image-uri $REPOSITORY_URI:$IMAGE_TAG --region $REGION --profile $PROFILE"
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to update function code after retries"
        exit 1
    fi
    
    # Wait for code update to complete before updating configuration
    if ! wait_for_function_ready $FUNCTION_NAME; then
        echo "❌ Function code update verification failed"
        exit 1
    fi
    
    # Update function configuration with retry logic
    echo "🔄 Updating function configuration..."
    update_lambda_with_retry "Updating function configuration" \
        "aws lambda update-function-configuration --function-name $FUNCTION_NAME --timeout 300 --memory-size 256 --environment Variables='{VERTEX_AI_PROJECT_ID=$VERTEX_AI_PROJECT_ID,VERTEX_AI_LOCATION=${VERTEX_AI_LOCATION:-asia-northeast1},API_KEY=$API_KEY,GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS}' --region $REGION --profile $PROFILE"
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to update function configuration after retries"
        exit 1
    fi
    
    # Final verification
    if ! wait_for_function_ready $FUNCTION_NAME; then
        echo "❌ Function configuration update verification failed"
        exit 1
    fi
    
    echo "✅ Lambda function updated successfully"
else
    echo "Creating new Lambda function..."
    
    # Create execution role if it doesn't exist
    ROLE_NAME="essam-ocr-lambda-role"
    ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
    
    if ! aws iam get-role --role-name $ROLE_NAME --profile $PROFILE > /dev/null 2>&1; then
        echo "Creating IAM role for Lambda..."
        
        # Create trust policy
        cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
        
        aws iam create-role \
            --role-name $ROLE_NAME \
            --assume-role-policy-document file://trust-policy.json \
            --profile $PROFILE
        
        # Attach basic Lambda execution policy
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
            --profile $PROFILE
        
        # Create and attach policy for Vertex AI access (if needed for cross-cloud access)
        # Note: This Lambda uses Vertex AI client library which handles authentication via service account
        cat > vertex-ai-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "*"
    }
  ]
}
EOF
        
        aws iam put-role-policy \
            --role-name $ROLE_NAME \
            --policy-name VertexAIAccess \
            --policy-document file://vertex-ai-policy.json \
            --profile $PROFILE
        
        # Wait for role to be available
        echo "Waiting for IAM role to be available..."
        sleep 10
        
        rm trust-policy.json vertex-ai-policy.json
        echo "✅ IAM role created with Vertex AI permissions"
    else
        echo "✅ IAM role already exists"
    fi
    
    # Create Lambda function
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$REPOSITORY_URI:$IMAGE_TAG \
        --role $ROLE_ARN \
        --timeout 300 \
        --memory-size 256 \
        --environment Variables="{VERTEX_AI_PROJECT_ID=$VERTEX_AI_PROJECT_ID,VERTEX_AI_LOCATION=${VERTEX_AI_LOCATION:-asia-northeast1},API_KEY=$API_KEY,GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS}" \
        --region $REGION \
        --profile $PROFILE
    
    echo "✅ Lambda function created successfully"
fi

# Step 7: Create Function URL (public endpoint)
echo "📋 Step 7: Creating/updating Function URL..."

if aws lambda get-function-url-config --function-name $FUNCTION_NAME --region $REGION --profile $PROFILE > /dev/null 2>&1; then
    echo "Function URL already exists"
    FUNCTION_URL=$(aws lambda get-function-url-config \
        --function-name $FUNCTION_NAME \
        --region $REGION \
        --profile $PROFILE \
        --query FunctionUrl \
        --output text)
else
    echo "Creating Function URL..."
    FUNCTION_URL=$(aws lambda create-function-url-config \
        --function-name $FUNCTION_NAME \
        --auth-type NONE \
        --cors AllowCredentials=false,AllowMethods=["POST"],AllowOrigins=["*"],AllowHeaders=["content-type","authorization"] \
        --region $REGION \
        --profile $PROFILE \
        --query FunctionUrl \
        --output text)
fi

# Add resource-based policy to allow public access
echo "📋 Adding resource-based policy for public access..."
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id FunctionURLAllowPublicAccess \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type NONE \
    --region $REGION \
    --profile $PROFILE 2>/dev/null || {
    echo "Permission already exists or failed to add (this is usually okay)"
}

echo "✅ Function URL configured"

# Step 8: Display deployment information
echo ""
echo "🎉 Deployment completed successfully!"

# Final status check
echo ""
echo "📋 Final Function Status:"
check_lambda_status $FUNCTION_NAME > /dev/null 2>&1 || true
aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --profile $PROFILE \
    --query '{
        State: Configuration.State,
        LastUpdateStatus: Configuration.LastUpdateStatus,
        LastModified: Configuration.LastModified,
        MemorySize: Configuration.MemorySize,
        Timeout: Configuration.Timeout,
        CodeSize: Configuration.CodeSize
    }' --output table

echo ""
echo "📊 Deployment Summary:"
echo "  Function Name: $FUNCTION_NAME"
echo "  Region: $REGION"
echo "  ECR Repository: $REPOSITORY_URI"
echo "  Function URL: $FUNCTION_URL"
echo ""
echo "🧪 Test your endpoint:"
echo "curl -X POST $FUNCTION_URL \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'Authorization: Bearer YOUR_API_KEY' \\"
echo "  -d '{"
echo "    \"data\": \"<base64-encoded-file>\","
echo "    \"media_type\": \"image/jpeg\""
echo "  }'"
echo ""
echo "💡 Next steps:"
echo "  1. Replace YOUR_API_KEY with your actual API key in the curl command"
echo "  2. Test the endpoint with your tax adjustment document images"
echo "  3. Monitor function logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow --profile $PROFILE"
echo "  4. Check function status: $0 --status"
echo "  5. Update function as needed by re-running this script"