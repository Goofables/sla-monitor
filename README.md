## SLA Monitor
Simple script to ping services and save a log to a database that can be analyzed for uptime statistics.
Also a project for me to learn terraform and GCP. I use a google cloud scheduler to run a cloud function which pulls the data to a bigquery table.


# Setup:
* Get GCP credentials for your project
* Run `terraform apply`
* Create services in the database (no script for this yet)