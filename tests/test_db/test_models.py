from sqlalchemy import select

from db.connections import SessionLocal
from db.models.user import User
from db.models.strategy_template import StrategyTemplate
from db.models.strategy_requirement import StrategyRequirement
from db.models.strategy_subscription import StrategySubscription


# ---------------------------------------------------------
# Test User ORM model
# ---------------------------------------------------------
def test_read_users():
    # Create a database session using our SQLAlchemy session factory.
    with SessionLocal() as session:

        # select(User) tells SQLAlchemy to fetch User ORM objects.
        users = session.scalars(select(User)).all()

        # We already inserted demo users into PostgreSQL,
        # so at least one user should be returned.
        assert len(users) > 0

        # Print the objects so we can visually verify the data.
        for user in users:
            print(
                user.id,
                user.email,
                user.is_active,
            )


# ---------------------------------------------------------
# Test StrategyTemplate ORM model
# ---------------------------------------------------------
def test_read_strategy_templates():
    # Open a database session.
    with SessionLocal() as session:

        # Fetch all strategy template records
        # and convert the rows into StrategyTemplate objects.
        strategies = session.scalars(
            select(StrategyTemplate)
        ).all()

        # Our 10 EMA strategy should exist.
        assert len(strategies) > 0

        # Display the data returned by SQLAlchemy.
        for strategy in strategies:
            print(
                strategy.id,
                strategy.name,
                strategy.strategy_type,
                strategy.is_active,
            )


# ---------------------------------------------------------
# Test StrategyRequirement ORM model
# ---------------------------------------------------------
def test_read_strategy_requirements():
    # Open a database session.
    with SessionLocal() as session:

        # Fetch all requirements associated with our strategies.
        requirements = session.scalars(
            select(StrategyRequirement)
        ).all()

        # At least the EMA and timeframe requirements should exist.
        assert len(requirements) > 0

        # Display the requirement data.
        for requirement in requirements:
            print(
                requirement.id,
                requirement.strategy_template_id,
                requirement.requirement_type,
                requirement.name,
                requirement.parameters,
            )


# ---------------------------------------------------------
# Test StrategySubscription ORM model
# ---------------------------------------------------------
def test_read_strategy_subscriptions():
    # Open a database session.
    with SessionLocal() as session:

        # Fetch all strategy subscriptions.
        subscriptions = session.scalars(
            select(StrategySubscription)
        ).all()

        # Our demo users should have subscriptions.
        assert len(subscriptions) > 0

        # Display the subscription data.
        for subscription in subscriptions:
            print(
                subscription.id,
                subscription.user_id,
                subscription.strategy_template_id,
                subscription.symbol,
                subscription.is_active,
            )