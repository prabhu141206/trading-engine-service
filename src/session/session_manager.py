from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from registry.strategy_models import StrategyGroup
from session.user_session import UserSession
from registry.subscription_registry import SubscriptionRegistry
from registry.strategy_registry import StrategyRegistry

class SessionManager:
    """
    Manage runtime user sessions.

    Responsibilities
    ----------------
    - Listen to market lifecycle events.
    - Load active users when market opens.
    - Create in-memory runtime sessions.
    - Populate SubscriptionRegistry.
    - Populate StrategyRegistry.
    - Clear sessions when market closes.
    """

    def __init__(
        self,
        event_bus: EventBus,
        subscription_registry: SubscriptionRegistry,
        strategy_registry: StrategyRegistry,
    ) -> None:

        # Dependency injection
        self._event_bus = event_bus
        self._subscription_registry = subscription_registry
        self._strategy_registry = strategy_registry

        # Active runtime sessions.
        self._sessions: dict[int, UserSession] = {}

    # ---------------------------------------------------------
    # Temporary data source
    # ---------------------------------------------------------

    def _load_active_users(self) -> list[UserSession]:
        """
        Temporary in-memory user configuration.

        Future implementation:
            - Query active users from database.
            - Query active symbol subscriptions.
            - Query selected strategies.
            - Build UserSession objects.
        """

        ema_nifty = StrategyGroup(
            strategy_type="EMA",
            symbol="NIFTY",
            timeframe="5m",
            parameters=(("period", 10),),
        )

        ema_banknifty = StrategyGroup(
            strategy_type="EMA",
            symbol="BANKNIFTY",
            timeframe="5m",
            parameters=(("period", 10),),
        )

        ema_finnifty = StrategyGroup(
            strategy_type="EMA",
            symbol="FINNIFTY",
            timeframe="5m",
            parameters=(("period", 10),),
        )

        return [
            UserSession(
                user_id=101,
                subscribed_symbols={"NIFTY", "BANKNIFTY"},
                strategies={
                    ema_nifty,
                    ema_banknifty,
                },
            ),

            UserSession(
                user_id=202,
                subscribed_symbols={"NIFTY"},
                strategies={
                    ema_nifty,
                },
            ),

            UserSession(
                user_id=303,
                subscribed_symbols={"FINNIFTY"},
                strategies={
                    ema_finnifty,
                },
            ),
        ]

    # ---------------------------------------------------------
    # Session lifecycle
    # ---------------------------------------------------------

    def _create_user_sessions(self) -> None:
        """
        Create runtime sessions and register their
        market-data and strategy requirements.
        """

        active_sessions = self._load_active_users()

        for session in active_sessions:

            # Store runtime user session.
            self._sessions[session.user_id] = session

            # Register required market-data symbols.
            for symbol in session.subscribed_symbols:
                self._subscription_registry.add_symbol(symbol)

            # Register unique strategy groups.
            for strategy in session.strategies:
                self._strategy_registry.add_strategy(strategy)


    def _clear_user_sessions(self) -> None:
        """
        Remove all runtime sessions and registry state.
        """

        self._sessions.clear()

        self._subscription_registry.clear()
        self._strategy_registry.clear()

    # ---------------------------------------------------------
    # Event registration
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Register market lifecycle event handlers.
        """

        self._event_bus.subscribe(
            EventType.MARKET_OPEN,
            self._on_market_open
        )

        self._event_bus.subscribe(
            EventType.MARKET_CLOSE,
            self._on_market_close
        )

    # ---------------------------------------------------------
    # Event handlers
    # ---------------------------------------------------------

    def _on_market_open(
        self,
        event: Event
    ) -> None:
        """
        Handle MARKET_OPEN event.
        """

        self._create_user_sessions()

    def _on_market_close(
        self,
        event: Event
    ) -> None:
        """
        Handle MARKET_CLOSE event.
        """

        self._clear_user_sessions()