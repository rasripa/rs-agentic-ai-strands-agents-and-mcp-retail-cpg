# Prerequisites — data setup

Run this before Lab 0. It creates the DynamoDB tables the agents query and loads the synthetic
sample data, and it provides the documents used to build the knowledge base.

## What's here

- `create_tables.py` — creates the DynamoDB tables and loads them from the CSV files
- `data_files/product_inventory/product_inventory.csv` — stock levels, warehouse locations,
  reorder thresholds
- `data_files/product_reviews/product_reviews.csv` — ratings and review text
- `data_files/anycompany-dataset/` — the fictional AnyCompany policy set (shipping, returns,
  privacy, account management, terms, FAQ) plus a company profile PDF. These are the source
  documents for the FAQ and Policy knowledge base used from Lab 1 onwards.

All data is synthetic. AnyCompany is a fictional retailer.

## Steps

1. Configure AWS credentials for the account you'll use, and confirm Amazon Bedrock model access
   is enabled for the models in the labs.
2. Install the dependencies from the repository-root `requirements.txt`.
3. Create and populate the tables:

   ```bash
   python create_tables.py
   ```

4. Create a Bedrock Knowledge Base over `data_files/anycompany-dataset/` and note the knowledge
   base ID — later labs read it from SSM Parameter Store under `faq_kb_id`.

## Notes

- The scripts default to **us-west-2**. If you work in another region, set `AWS_REGION` and check
  Bedrock model availability there first.
