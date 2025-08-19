#!/bin/bash

# Start Flask development server for meal-planner-aws-lambda
# Run this in a separate terminal tab

echo "=========================================="
echo "Starting Meal Planner Development Server"
echo "=========================================="
echo ""

# Already in backend directory, no need to cd
# Set environment to use local Docker PostgreSQL
export USE_LOCAL_DB=true

# Start Flask server on port 5050 (avoiding conflict with AirPlay on 5000)
echo "Starting Flask server on http://localhost:5050"
echo "Using local Docker PostgreSQL database"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

# Run the Flask app
python -m app
