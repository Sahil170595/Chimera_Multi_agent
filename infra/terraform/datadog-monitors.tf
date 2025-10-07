# Terraform configuration for Datadog monitors (optional)

terraform {
  required_providers {
    datadog = {
      source = "DataDog/datadog"
    }
  }
}

provider "datadog" {
  api_key = var.datadog_api_key
  app_key = var.datadog_app_key
}

variable "datadog_api_key" {
  description = "Datadog API key"
  type        = string
}

variable "datadog_app_key" {
  description = "Datadog application key"
  type        = string
}

# Monitor for episode generation failures
resource "datadog_monitor" "episode_generation_failures" {
  name               = "Muse Protocol - Episode Generation Failures"
  type               = "metric alert"
  query              = "sum(last_5m):sum:muse.episode.count{status:error}.as_count() > 0"
  message            = "Episode generation is failing. Check logs for details."
  escalation_message = "Episode generation has been failing for more than 5 minutes."
  
  monitor_thresholds {
    warning  = 0
    critical = 1
  }
  
  tags = ["service:muse-protocol", "team:platform"]
}

# Monitor for high episode latency
resource "datadog_monitor" "high_episode_latency" {
  name               = "Muse Protocol - High Episode Latency"
  type               = "metric alert"
  query              = "avg(last_10m):avg:muse.episode.latency_p95{*} > 10000"
  message            = "Episode generation latency is high (>10s)."
  
  monitor_thresholds {
    warning  = 5000
    critical = 10000
  }
  
  tags = ["service:muse-protocol", "team:platform"]
}

# Monitor for translation failures
resource "datadog_monitor" "translation_failures" {
  name               = "Muse Protocol - Translation Failures"
  type               = "metric alert"
  query              = "sum(last_5m):sum:muse.translation.count{status:error}.as_count() > 0"
  message            = "Translation sync is failing. Check DeepL API status."
  
  monitor_thresholds {
    warning  = 0
    critical = 1
  }
  
  tags = ["service:muse-protocol", "team:platform"]
}



