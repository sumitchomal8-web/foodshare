from pydantic import ValidationError
import pytest
from app.schemas.user import UserRegister


# Shared valid registration data for a donor
def valid_donor_data():
    return {
        "name": "Rahul Sharma",
        "email": "rahul@example.com",
        "password": "securepass123",
        "phone": "9876543210",
        "role": "DONOR",
        "address": {
            "street": "MG Road",
            "city": "Jaipur",
            "state": "Rajasthan",
            "pincode": "302001",
        },
    }

# Test 1: Valid donor registration
def test_valid_donor_registration():
    data = valid_donor_data()

    user = UserRegister(**data)

    assert user.name == "Rahul Sharma"
    assert user.email == "rahul@example.com"
    assert user.role == "DONOR"
    assert user.ngo_profile is None


# Test 2: Valid NGO registration
def test_valid_ngo_registration():
    data = valid_donor_data()
    data["role"] = "NGO"
    data["ngo_profile"] = {
        "organization_name": "Helping Hands",
        "org_type": "NGO",
        "registration_number": "NGO12345",
    }

    user = UserRegister(**data)

    assert user.role == "NGO"
    assert user.ngo_profile.organization_name == "Helping Hands"


# Test 3: Password shorter than eight characters
def test_short_password_rejected():
    data = valid_donor_data()
    data["password"] = "abc"

    with pytest.raises(ValidationError):
        UserRegister(**data)


# Test 4: Invalid role must be rejected
def test_admin_role_rejected():
    data = valid_donor_data()
    data["role"] = "ADMIN"

    with pytest.raises(ValidationError):
        UserRegister(**data)


# Test 5: NGO without an NGO profile must be rejected
def test_ngo_without_profile_rejected():
    data = valid_donor_data()
    data["role"] = "NGO"

    with pytest.raises(ValidationError):
        UserRegister(**data)


# Test 6: Donor with an NGO profile must be rejected
def test_donor_with_ngo_profile_rejected():
    data = valid_donor_data()
    data["ngo_profile"] = {
        "organization_name": "Helping Hands",
        "org_type": "NGO",
        "registration_number": "NGO12345",
    }

    with pytest.raises(ValidationError):
        UserRegister(**data)


# Test 7: Unexpected is_admin field must be rejected
def test_unexpected_field_rejected():
    data = valid_donor_data()
    data["is_admin"] = True

    with pytest.raises(ValidationError):
        UserRegister(**data)


# Test 8: Invalid email must be rejected
def test_invalid_email_rejected():
    data = valid_donor_data()
    data["email"] = "not-an-email"

    with pytest.raises(ValidationError):
        UserRegister(**data)


# Test 9: Missing required address field must be rejected
def test_missing_address_field_rejected():
    data = valid_donor_data()
    del data["address"]["city"]

    with pytest.raises(ValidationError):
        UserRegister(**data)

