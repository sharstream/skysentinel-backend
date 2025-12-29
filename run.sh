#!/bin/bash

# export OPENSKY_CLIENT_ID=client_id
# export OPENSKY_CLIENT_SECRET=client_secret

# export OPENSKY_OAUTH2_TOKEN=$(curl -X POST "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token" \
#   -H "Content-Type: application/x-www-form-urlencoded" \
#   -d "grant_type=client_credentials" \
#   -d "client_id=$OPENSKY_CLIENT_ID" \
#   -d "client_secret=$OPENSKY_CLIENT_SECRET" | jq -r .access_token)

# curl -X GET "https://opensky-network.org/api/states/all" \
#   -H "Authorization: Bearer $OPENSKY_OAUTH2_TOKEN" \
#   -H "Content-Type: application/json"

# Activate virtual environment
source venv/bin/activate

# Run the FastAPI server
python app/main.py

# echo "OPENSKY_OAUTH2_TOKEN: $OPENSKY_OAUTH2_TOKEN"
