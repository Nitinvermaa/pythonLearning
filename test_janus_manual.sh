#!/bin/bash
# Manual Janus API Testing Script
# Tests each step of Janus WebRTC setup

set -e

JANUS_URL="${JANUS_URL:-http://localhost:8088/janus}"
ROOM_ID="${ROOM_ID:-1234}"

echo "=========================================="
echo "Janus Manual API Test"
echo "=========================================="
echo "Janus URL: $JANUS_URL"
echo "Room ID: $ROOM_ID"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to make API calls
api_call() {
    local endpoint=$1
    local data=$2
    local method=${3:-POST}
    
    if [ "$method" = "GET" ]; then
        curl -s -X GET "$endpoint"
    else
        curl -s -X POST "$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data"
    fi
}

# Step 1: Check Janus is running
echo -e "${YELLOW}Step 1: Checking Janus server...${NC}"
RESPONSE=$(api_call "$JANUS_URL" '{"janus":"info","transaction":"check"}')
if echo "$RESPONSE" | jq -e '.janus == "success"' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Janus is running${NC}"
    echo "$RESPONSE" | jq '.data | {version_string, version}'
else
    echo -e "${RED}✗ Janus is not responding${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi
echo ""

# Step 2: Create session
echo -e "${YELLOW}Step 2: Creating session...${NC}"
TRANSACTION="session_$(date +%s)"
SESSION_RESPONSE=$(api_call "$JANUS_URL" "{\"janus\":\"create\",\"transaction\":\"$TRANSACTION\"}")
SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.data.id // empty')

if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
    echo -e "${RED}✗ Failed to create session${NC}"
    echo "$SESSION_RESPONSE" | jq .
    exit 1
fi

echo -e "${GREEN}✓ Session created: $SESSION_ID${NC}"
echo "$SESSION_RESPONSE" | jq '.data'
echo ""

# Step 3: Attach to VideoRoom plugin
echo -e "${YELLOW}Step 3: Attaching to VideoRoom plugin...${NC}"
TRANSACTION="attach_$(date +%s)"
ATTACH_RESPONSE=$(api_call "$JANUS_URL/$SESSION_ID" "{\"janus\":\"attach\",\"plugin\":\"janus.plugin.videoroom\",\"transaction\":\"$TRANSACTION\"}")
HANDLE_ID=$(echo "$ATTACH_RESPONSE" | jq -r '.data.id // empty')

if [ -z "$HANDLE_ID" ] || [ "$HANDLE_ID" = "null" ]; then
    echo -e "${RED}✗ Failed to attach to plugin${NC}"
    echo "$ATTACH_RESPONSE" | jq .
    exit 1
fi

echo -e "${GREEN}✓ Attached to plugin: $HANDLE_ID${NC}"
echo "$ATTACH_RESPONSE" | jq '.data'
echo ""

# Step 4: List rooms
echo -e "${YELLOW}Step 4: Listing rooms...${NC}"
TRANSACTION="list_$(date +%s)"
LIST_RESPONSE=$(api_call "$JANUS_URL/$SESSION_ID/$HANDLE_ID" "{\"janus\":\"message\",\"transaction\":\"$TRANSACTION\",\"body\":{\"request\":\"list\"}}")
echo "$LIST_RESPONSE" | jq '.plugindata.data.list // []'
echo ""

# Step 5: Create/Join room as publisher
echo -e "${YELLOW}Step 5: Joining room $ROOM_ID as publisher...${NC}"
TRANSACTION="join_$(date +%s)"
JOIN_RESPONSE=$(api_call "$JANUS_URL/$SESSION_ID/$HANDLE_ID" "{
    \"janus\":\"message\",
    \"transaction\":\"$TRANSACTION\",
    \"body\":{
        \"request\":\"join\",
        \"ptype\":\"publisher\",
        \"room\":$ROOM_ID,
        \"display\":\"Manual Test Publisher\"
    }
}")

if echo "$JOIN_RESPONSE" | jq -e '.plugindata.data.videoroom == "joined"' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Joined room $ROOM_ID${NC}"
    PUBLISHER_ID=$(echo "$JOIN_RESPONSE" | jq -r '.plugindata.data.id')
    echo "Publisher ID: $PUBLISHER_ID"
    echo "$JOIN_RESPONSE" | jq '.plugindata.data'
else
    echo -e "${YELLOW}⚠ Room join response:${NC}"
    echo "$JOIN_RESPONSE" | jq .
    # Don't exit, room might already exist
fi
echo ""

# Step 6: List participants
echo -e "${YELLOW}Step 6: Listing participants in room $ROOM_ID...${NC}"
TRANSACTION="participants_$(date +%s)"
PARTICIPANTS_RESPONSE=$(api_call "$JANUS_URL/$SESSION_ID/$HANDLE_ID" "{
    \"janus\":\"message\",
    \"transaction\":\"$TRANSACTION\",
    \"body\":{
        \"request\":\"listparticipants\",
        \"room\":$ROOM_ID
    }
}")

PARTICIPANTS=$(echo "$PARTICIPANTS_RESPONSE" | jq -r '.plugindata.data.participants // []')
PARTICIPANT_COUNT=$(echo "$PARTICIPANTS" | jq 'length')
echo "Participants: $PARTICIPANT_COUNT"
echo "$PARTICIPANTS" | jq .
echo ""

# Step 7: Check for SDP in responses
echo -e "${YELLOW}Step 7: Checking for SDP in responses...${NC}"
if echo "$JOIN_RESPONSE" | jq -e '.jsep' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ SDP found in join response${NC}"
    SDP_TYPE=$(echo "$JOIN_RESPONSE" | jq -r '.jsep.type')
    echo "SDP Type: $SDP_TYPE"
    if [ "$SDP_TYPE" != "null" ]; then
        echo "SDP Preview (first 200 chars):"
        echo "$JOIN_RESPONSE" | jq -r '.jsep.sdp' | head -c 200
        echo "..."
    fi
else
    echo "No SDP in join response (this is normal for publisher without offer)"
fi
echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}✓ Session ID: $SESSION_ID${NC}"
echo -e "${GREEN}✓ Handle ID: $HANDLE_ID${NC}"
echo -e "${GREEN}✓ Room ID: $ROOM_ID${NC}"
echo ""
echo "Next steps:"
echo "1. Run publisher: python3 janus_webrtc_client.py --room-id $ROOM_ID"
echo "2. Check participants again:"
echo "   curl -s -X POST \"$JANUS_URL/$SESSION_ID/$HANDLE_ID\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"janus\":\"message\",\"transaction\":\"check\",\"body\":{\"request\":\"listparticipants\",\"room\":$ROOM_ID}}' | jq '.plugindata.data.participants'"
echo ""
echo "To view SDP content:"
echo "  echo \"\$JOIN_RESPONSE\" | jq -r '.jsep.sdp'"
echo ""
