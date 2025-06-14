terraform {
  required_version = ">= 1.12.2"

  backend "s3" {
    bucket = "gatech-me-robojackets-channel-events-statefiles"
    region = "us-east-1"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.0.0-beta3"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "environment_name" {
  type        = string
  description = "The name of the environment"
}

data "aws_iam_policy_document" "allow_lambda_to_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_function" {
  name = "channel-events-${var.environment_name}"

  assume_role_policy = data.aws_iam_policy_document.allow_lambda_to_assume_role.json
}

data "aws_iam_policy" "cloudwatch" {
  arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy" "xray" {
  arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_iam_role_policy_attachment" "cloudwatch" {
  role       = aws_iam_role.lambda_function.name
  policy_arn = data.aws_iam_policy.cloudwatch.arn
}

resource "aws_iam_role_policy_attachment" "xray" {
  role       = aws_iam_role.lambda_function.name
  policy_arn = data.aws_iam_policy.xray.arn
}

resource "aws_lambda_function" "lambda_function" {
  region = "us-east-1"

  function_name = "channel-events-${var.environment_name}"
  description   = "Post a notification in Slack when a channel is created or modified"

  role = aws_iam_role.lambda_function.arn

  runtime       = "python3.13"
  architectures = ["arm64"]

  environment {
    variables = {
      SLACK_SIGNING_SECRET = sensitive("")
      SLACK_API_TOKEN      = sensitive("")
      SLACK_NOTIFY_CHANNEL = sensitive("")
    }
  }

  package_type     = "Zip"
  filename         = "./_bundle.zip"
  handler          = "handler.handler"
  source_code_hash = filebase64sha256("./_bundle.zip")

  memory_size = 512
  timeout     = 30

  tracing_config {
    mode = "Active"
  }

  lifecycle {
    ignore_changes = [
      environment
    ]
  }
}

resource "aws_lambda_function_url" "function_url" {
  region = "us-east-1"

  function_name      = aws_lambda_function.lambda_function.arn
  authorization_type = "NONE"
}

# https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html#urls-auth-none
resource "aws_lambda_permission" "allow_cloudwatch" {
  region = "us-east-1"

  statement_id           = "AllowUnauthenticatedAccessToInvokeFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.lambda_function.function_name
  principal              = "*"
  function_url_auth_type = "NONE"

  lifecycle {
    replace_triggered_by = [
      aws_lambda_function.lambda_function
    ]
  }
}

output "function_url" {
  value = aws_lambda_function_url.function_url.function_url
}
