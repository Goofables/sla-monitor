variable "project" {
  type        = string
  description = "Google project ID"
}

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.2.0"
    }
  }
}

provider "google" {
  credentials = file("sla-monitor.json")
  project     = var.project
  region      = "us-central1"
}

data "archive_file" "function_source_zip" {
  output_path = "sla-monitor.zip"
  type        = "zip"
  source_dir  = "function_code"
}

resource "google_storage_bucket" "function_source_bucket" {
  name                        = "sla-monitor-function-storage"
  uniform_bucket_level_access = true
  location                    = "us"
}

resource "google_storage_bucket_object" "function_source" {
  name   = "sla-monitor.${data.archive_file.function_source_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_source_bucket.id
  source = data.archive_file.function_source_zip.output_path
}

resource "google_cloudfunctions_function" "sla_monitor_function" {
  name                  = "sla-monitor"
  description           = "Check for service outages and notify"
  available_memory_mb   = 128
  max_instances         = 1
  min_instances         = 0
  timeout               = 60
  source_archive_bucket = google_storage_bucket.function_source_bucket.name
  source_archive_object = google_storage_bucket_object.function_source.name

  trigger_http = true
  runtime      = "python311"
  entry_point  = "run_checks"
}

data "google_compute_default_service_account" "default" {}

resource "google_cloud_scheduler_job" "sla_monitor_job" {
  name        = "sla-monitor-job"
  description = "Trigger sla-monitor"
  schedule    = "* * * * *"
  time_zone   = "Etc/UTC"

  http_target {
    http_method = "GET"
    oidc_token {
      service_account_email = data.google_compute_default_service_account.default.email
    }
    uri = google_cloudfunctions_function.sla_monitor_function.https_trigger_url
  }
}


resource "google_bigquery_dataset" "sla_dataset" {
  dataset_id = "sla"
}

resource "google_bigquery_table" "services_table" {
  dataset_id          = google_bigquery_dataset.sla_dataset.dataset_id
  table_id            = "services"
  deletion_protection = true
  schema              = jsonencode([
    {
      name = "id"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "name"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "owner_discord_id"
      type = "INT64"
      mode = "REQUIRED"
    },
    {
      name = "check_type"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "check_subject"
      type = "STRING"
      mode = "REQUIRED"
    }
  ])
}

resource "google_bigquery_table" "log_table" {
  dataset_id          = google_bigquery_dataset.sla_dataset.dataset_id
  table_id            = "log"
  deletion_protection = true
  schema              = jsonencode([
    {
      name = "service_id"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "status"
      type = "BOOLEAN"
      mode = "REQUIRED"
    },
    {
      name = "time"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    }
  ])
}
