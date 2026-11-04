import pytest

import model_fakes


@pytest.fixture
def config():
    return model_fakes.make_config(monthly_hard_usd=100, monthly_soft_usd=80, run_default_usd=5)
