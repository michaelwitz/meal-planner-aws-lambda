"""Flask app entry point for running with python -m app."""

import os
from app import create_app

# Determine config based on USE_LOCAL_DB environment variable
use_local = os.environ.get('USE_LOCAL_DB', 'true').lower() == 'true'
config_name = 'development-local' if use_local else 'development-cloud'

# Create and run the app
app = create_app(config_name)

if __name__ == '__main__':
    print(f"\n{'='*50}")
    print(f"Starting Flask app with config: {config_name}")
    print(f"Database: {'Local Docker PostgreSQL' if use_local else 'Cloud RDS Serverless'}")
    print(f"{'='*50}\n")
    
    app.run(
        host='0.0.0.0',
        port=5050,
        debug=True
    )
