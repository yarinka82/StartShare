import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from backend.apps.investors.models import InvestorProfile
from backend.apps.profiles.models import StartupProfile
from backend.apps.introductions.models import Introduction, IntroductionStatus


@pytest.fixture
def user_model():
    return get_user_model()


@pytest.fixture
def investor_user(db, user_model):
    return user_model.objects.create_user(
        username="investor-user",
        email="investor@example.com",
        password="password123",
    )


@pytest.fixture
def startup_user(db, user_model):
    return user_model.objects.create_user(
        username="startup-user",
        email="startup@example.com",
        password="password123",
    )


@pytest.fixture
def stranger_user(db, user_model):
    return user_model.objects.create_user(
        username="stranger-user",
        email="stranger@example.com",
        password="password123",
    )


@pytest.fixture
def investor_profile(db, investor_user):
    return InvestorProfile.objects.create(
        owner=investor_user,
        organization_name="Northstar Capital",
        organization_type="Fund",
        contact_name="Investor Contact",
        contact_email="investor-contact@example.com",
    )


@pytest.fixture
def startup_profile(db, startup_user):
    return StartupProfile.objects.create(
        owner=startup_user,
        company_name="Alpha Startup",
        contact_name="Startup Contact",
        contact_email="startup-contact@example.com",
        profile_status=StartupProfile.STATUS_LIVE,
    )


@pytest.fixture
def introduction(db, startup_profile, investor_profile):
    return Introduction.objects.create(
        startup=startup_profile,
        investor=investor_profile,
        status=IntroductionStatus.SUGGESTED,
    )


@pytest.fixture
def investor_token(db, investor_user):
    token, _ = Token.objects.get_or_create(user=investor_user)
    return token.key


@pytest.fixture
def startup_token(db, startup_user):
    token, _ = Token.objects.get_or_create(user=startup_user)
    return token.key


@pytest.fixture
def stranger_token(db, stranger_user):
    token, _ = Token.objects.get_or_create(user=stranger_user)
    return token.key


@pytest.fixture
def investor_api_client(investor_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {investor_token}")
    return client


@pytest.fixture
def startup_api_client(startup_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {startup_token}")
    return client


@pytest.fixture
def stranger_api_client(stranger_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {stranger_token}")
    return client
