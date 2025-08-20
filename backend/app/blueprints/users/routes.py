from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.blueprints.users import bp
from app.models.entities import User
from app.models.database import db
from app.utils.validation import validate_with_422 as validate
from app.schemas.user_schemas import UserUpdateSchema, UserResponseSchema, PasswordChangeSchema
from app.services.auth_service import AuthService


@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get detailed profile information for the current user."""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    return jsonify(UserResponseSchema.model_validate(user).model_dump())



@bp.route('/me/password', methods=['PUT'])
@jwt_required()
@validate(body=PasswordChangeSchema)
def change_password(body: PasswordChangeSchema):
    """Change the current user's password."""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    
    # Validate current password
    if not AuthService.verify_password(user, body.currentPassword):
        return jsonify({'error': 'Invalid current password'}), 403
    
    # Update to new password
    user.update_password(body.newPassword)
    db.session.commit()
    
    return '', 204


@bp.route('/me', methods=['PUT'])
@jwt_required()
@validate(body=UserUpdateSchema)
def update_current_user(body: UserUpdateSchema):
    """Update the current user's profile information."""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    
    # Update allowed fields
    user.fullName = body.fullName if body.fullName is not None else user.fullName
    user.sex = body.sex if body.sex is not None else user.sex
    user.phoneNumber = body.phoneNumber if body.phoneNumber is not None else user.phoneNumber
    user.addressLine1 = body.addressLine1 if body.addressLine1 is not None else user.addressLine1
    user.addressLine2 = body.addressLine2 if body.addressLine2 is not None else user.addressLine2
    user.city = body.city if body.city is not None else user.city
    user.stateProvinceCode = body.stateProvinceCode if body.stateProvinceCode is not None else user.stateProvinceCode
    user.countryCode = body.countryCode.upper() if body.countryCode is not None else user.countryCode
    user.postalCode = body.postalCode if body.postalCode is not None else user.postalCode
    
    db.session.commit()
    return jsonify(UserResponseSchema.model_validate(user).model_dump())
