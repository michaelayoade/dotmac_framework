# AWS Compute Module for DotMac ISP Instance Deployment

# Data sources for AMI and VPC
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Launch Template for DotMac Instance
resource "aws_launch_template" "dotmac_instance" {
  name_prefix   = "${var.tenant_id}-dotmac-"
  image_id      = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = var.key_pair_name

  vpc_security_group_ids = [aws_security_group.dotmac_instance.id]

  # User data script for initial setup
  user_data = base64encode(templatefile("${path.module}/templates/user_data.sh", {
    tenant_id           = var.tenant_id
    environment         = var.environment
    openbao_addr       = var.openbao_addr
    openbao_token      = var.openbao_token
    signoz_endpoint    = var.signoz_endpoint
    management_api_url = var.management_api_url
  }))

  # Instance metadata options
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                = "required"
    http_put_response_hop_limit = 2
    instance_metadata_tags     = "enabled"
  }

  # EBS optimization
  ebs_optimized = true

  # Root volume configuration
  block_device_mappings {
    device_name = "/dev/sda1"
    ebs {
      volume_type           = "gp3"
      volume_size           = var.root_volume_size
      delete_on_termination = true
      encrypted             = true
    }
  }

  # Additional data volume for DotMac data
  block_device_mappings {
    device_name = "/dev/sdf"
    ebs {
      volume_type           = "gp3"
      volume_size           = var.data_volume_size
      delete_on_termination = false
      encrypted             = true
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = merge(var.common_tags, {
      Name      = "${var.tenant_id}-dotmac-instance"
      TenantId  = var.tenant_id
      Component = "dotmac-platform"
    })
  }

  tag_specifications {
    resource_type = "volume"
    tags = merge(var.common_tags, {
      Name      = "${var.tenant_id}-dotmac-volume"
      TenantId  = var.tenant_id
      Component = "storage"
    })
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "dotmac_instances" {
  name                = "${var.tenant_id}-dotmac-asg"
  vpc_zone_identifier = var.private_subnet_ids
  target_group_arns   = [aws_lb_target_group.dotmac_web.arn, aws_lb_target_group.dotmac_api.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300

  min_size         = var.min_instances
  max_size         = var.max_instances
  desired_capacity = var.desired_instances

  launch_template {
    id      = aws_launch_template.dotmac_instance.id
    version = "$Latest"
  }

  # Instance refresh configuration
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup       = 300
    }
  }

  # Lifecycle hooks for graceful shutdown
  initial_lifecycle_hook {
    name                 = "${var.tenant_id}-dotmac-shutdown"
    default_result       = "ABANDON"
    heartbeat_timeout    = 300
    lifecycle_transition = "autoscaling:EC2_INSTANCE_TERMINATING"
  }

  tag {
    key                 = "Name"
    value               = "${var.tenant_id}-dotmac-instance"
    propagate_at_launch = true
  }

  tag {
    key                 = "TenantId"
    value               = var.tenant_id
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  dynamic "tag" {
    for_each = var.common_tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }
}

# Security Group for DotMac Instance
resource "aws_security_group" "dotmac_instance" {
  name_prefix = "${var.tenant_id}-dotmac-"
  description = "Security group for DotMac ISP instance"
  vpc_id      = var.vpc_id

  # HTTP access from load balancer
  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.dotmac_alb.id]
  }

  # HTTPS access from load balancer
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.dotmac_alb.id]
  }

  # API access from load balancer
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.dotmac_alb.id]
  }

  # SSH access from bastion or management
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  # Database access (PostgreSQL)
  ingress {
    from_port = 5432
    to_port   = 5432
    protocol  = "tcp"
    self      = true
  }

  # Redis access
  ingress {
    from_port = 6379
    to_port   = 6379
    protocol  = "tcp"
    self      = true
  }

  # SignOz monitoring ports
  ingress {
    from_port   = 4317
    to_port     = 4318
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name      = "${var.tenant_id}-dotmac-sg"
    TenantId  = var.tenant_id
    Component = "security"
  })
}

# Application Load Balancer
resource "aws_lb" "dotmac_alb" {
  name               = "${var.tenant_id}-dotmac-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.dotmac_alb.id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "production"

  # Access logs
  access_logs {
    bucket  = var.access_logs_bucket
    prefix  = "alb-logs/${var.tenant_id}"
    enabled = var.enable_access_logs
  }

  tags = merge(var.common_tags, {
    Name      = "${var.tenant_id}-dotmac-alb"
    TenantId  = var.tenant_id
    Component = "load-balancer"
  })
}

# ALB Security Group
resource "aws_security_group" "dotmac_alb" {
  name_prefix = "${var.tenant_id}-dotmac-alb-"
  description = "Security group for DotMac ALB"
  vpc_id      = var.vpc_id

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # All outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name      = "${var.tenant_id}-dotmac-alb-sg"
    TenantId  = var.tenant_id
    Component = "load-balancer-security"
  })
}

# Target Groups
resource "aws_lb_target_group" "dotmac_web" {
  name     = "${var.tenant_id}-dotmac-web"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }

  tags = merge(var.common_tags, {
    Name      = "${var.tenant_id}-dotmac-web-tg"
    TenantId  = var.tenant_id
    Component = "load-balancer-target"
  })
}

resource "aws_lb_target_group" "dotmac_api" {
  name     = "${var.tenant_id}-dotmac-api"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/api/health"
    matcher             = "200"
    port                = "8000"
    protocol            = "HTTP"
  }

  tags = merge(var.common_tags, {
    Name      = "${var.tenant_id}-dotmac-api-tg"
    TenantId  = var.tenant_id
    Component = "api-target"
  })
}

# ALB Listeners
resource "aws_lb_listener" "dotmac_web" {
  load_balancer_arn = aws_lb.dotmac_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "dotmac_web_https" {
  load_balancer_arn = aws_lb.dotmac_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.ssl_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.dotmac_web.arn
  }
}

# Auto Scaling Policies
resource "aws_autoscaling_policy" "scale_up" {
  name                   = "${var.tenant_id}-dotmac-scale-up"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown              = 300
  autoscaling_group_name = aws_autoscaling_group.dotmac_instances.name
}

resource "aws_autoscaling_policy" "scale_down" {
  name                   = "${var.tenant_id}-dotmac-scale-down"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown              = 300
  autoscaling_group_name = aws_autoscaling_group.dotmac_instances.name
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.tenant_id}-dotmac-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors ec2 cpu utilization"
  alarm_actions       = [aws_autoscaling_policy.scale_up.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.dotmac_instances.name
  }

  tags = merge(var.common_tags, {
    Name      = "${var.tenant_id}-dotmac-high-cpu-alarm"
    TenantId  = var.tenant_id
    Component = "monitoring"
  })
}

resource "aws_cloudwatch_metric_alarm" "low_cpu" {
  alarm_name          = "${var.tenant_id}-dotmac-low-cpu"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "25"
  alarm_description   = "This metric monitors ec2 cpu utilization"
  alarm_actions       = [aws_autoscaling_policy.scale_down.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.dotmac_instances.name
  }

  tags = merge(var.common_tags, {
    Name      = "${var.tenant_id}-dotmac-low-cpu-alarm"
    TenantId  = var.tenant_id
    Component = "monitoring"
  })
}