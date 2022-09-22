The `template.json` file in this directory was created as follows:
1. I copied the current collection template from ETL. It was last modified by Tom Augspurger on 6/30/22 via PR 965.
2. I edited the "msft:short_description" field to better align with the "msft:short_description" in the goes-glm collection. 
3. I added a new line for the group id: `"msft:group_id": "goes",`

That's it. Since `item_assets` was not touched, we _should_ be safe to ingest this new collection template into Staging.