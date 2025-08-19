"""Custom validation utilities."""

from functools import wraps
from flask import jsonify, request
from flask_pydantic import validate as flask_pydantic_validate
from pydantic import ValidationError


def validate_with_422(*args, **kwargs):
    """
    Custom wrapper around flask-pydantic's validate decorator that returns 422 for validation errors.
    
    This ensures proper HTTP status codes:
    - 422 Unprocessable Entity for validation errors
    - 400 Bad Request for other client errors
    """
    def decorator(func):
        # Apply flask-pydantic's validate decorator
        flask_validated = flask_pydantic_validate(*args, **kwargs)(func)
        
        @wraps(flask_validated)
        def wrapper(*inner_args, **inner_kwargs):
            try:
                # Call the flask-pydantic validated function
                response = flask_validated(*inner_args, **inner_kwargs)
                
                # Check if this is a validation error response from flask-pydantic
                if isinstance(response, tuple) and len(response) == 2:
                    body, status_code = response
                    if status_code == 400 and isinstance(body, dict) and 'validation_error' in body:
                        # Change status code to 422 for validation errors
                        return body, 422
                elif hasattr(response, 'json') and hasattr(response, 'status_code'):
                    # Handle Response objects
                    if response.status_code == 400:
                        try:
                            data = response.get_json()
                            if data and 'validation_error' in data:
                                return jsonify(data), 422
                        except:
                            pass
                
                return response
            except ValidationError as e:
                # Handle direct Pydantic validation errors
                return jsonify({'validation_error': e.errors()}), 422
            except Exception as e:
                # Let other exceptions bubble up
                raise
        
        return wrapper
    return decorator
