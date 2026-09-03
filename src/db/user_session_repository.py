from collections import defaultdict

from sqlalchemy import select

from db.connections import SessionLocal
from db.models.user import User
from db.models.strategy_template import StrategyTemplate
from db.models.strategy_requirement import StrategyRequirement
from db.models.strategy_subscription import StrategySubscription

from strategy.strategy_models import StrategyGroup
from session.user_session import UserSession


class UserSessionRepository:

    def get_active_sessions(self) -> list[UserSession]:
        # Open a database session for reading the persistent configuration.
        with SessionLocal() as session:

            # Fetch all active users with their active subscriptions
            # and active strategy templates.
            statement = (
                select(
                    User,
                    StrategySubscription,
                    StrategyTemplate,
                )
                .join(
                    StrategySubscription,
                    User.id == StrategySubscription.user_id,
                )
                .join(
                    StrategyTemplate,
                    StrategySubscription.strategy_template_id
                    == StrategyTemplate.id,
                )
                .where(
                    User.is_active.is_(True),
                    StrategySubscription.is_active.is_(True),
                    StrategyTemplate.is_active.is_(True),
                )
            )

            rows = session.execute(statement).all()

            # If there are no active configurations, there is
            # nothing to convert into runtime sessions.
            if not rows:
                return []

            # Get the strategy template IDs that are actually
            # being used by the active subscriptions.
            strategy_template_ids = {
                strategy.id
                for _, _, strategy in rows
            }

            # Fetch all requirements belonging to those strategies.
            requirement_rows = session.scalars(
                select(StrategyRequirement).where(
                    StrategyRequirement.strategy_template_id.in_(
                        strategy_template_ids
                    )
                )
            ).all()

            # Group requirements by strategy template.
            # This makes it easy to find all requirements for
            # a particular strategy.
            requirements_by_strategy = defaultdict(list)

            for requirement in requirement_rows:
                requirements_by_strategy[
                    requirement.strategy_template_id
                ].append(requirement)

            # Build the final UserSession objects.
            sessions_by_user = {}

            for user, subscription, strategy in rows:

                # Get all requirements for this strategy template.
                requirements = requirements_by_strategy[
                    strategy.id
                ]

                # Convert database requirements into the runtime
                # values expected by StrategyGroup.
                timeframe = None
                parameters = []

                for requirement in requirements:

                    if requirement.requirement_type == "TIMEFRAME":
                        timeframe = requirement.parameters["value"]

                    elif requirement.requirement_type == "INDICATOR":
                        # The database stores:
                        # name = "EMA"
                        # parameters = {"period": 10}
                        #
                        # But StrategyGroup expects:
                        # (("period", 10),)
                        parameters.append(
                            (
                                "period",
                                requirement.parameters["period"],
                            )
                        )

                # Make sure the strategy has the required timeframe.
                if timeframe is None:
                    raise ValueError(
                        f"Missing timeframe for strategy {strategy.id}"
                    )

                # Create the runtime StrategyGroup.
                strategy_group = StrategyGroup(
                    strategy_type=strategy.strategy_type,
                    symbol=subscription.symbol,
                    timeframe=timeframe,
                    parameters=tuple(parameters),
                )

                # Create the UserSession the first time we encounter
                # this user.
                if user.id not in sessions_by_user:
                    sessions_by_user[user.id] = UserSession(
                        user_id=user.id,
                        subscribed_symbols=set(),
                        strategies=set(),
                    )

                # Add the symbol to this user's market-data subscriptions.
                sessions_by_user[user.id].subscribed_symbols.add(
                    subscription.symbol
                )

                # Add the strategy configuration to the user's strategies.
                sessions_by_user[user.id].strategies.add(
                    strategy_group
                )

            return list(sessions_by_user.values())