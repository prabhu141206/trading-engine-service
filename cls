[1mdiff --git a/src/event_system/event_type.py b/src/event_system/event_type.py[m
[1mindex 9dd383b..76ca4fb 100644[m
[1m--- a/src/event_system/event_type.py[m
[1m+++ b/src/event_system/event_type.py[m
[36m@@ -18,5 +18,6 @@[m [mclass EventType(Enum):[m
     # INDICATOR EVENTS[m
     INDICATOR_BATCH_UPDATED = "INDICATOR_BATCH_UPDATED"[m
 [m
[32m+[m[32m    # STRATEGY EVENTS[m
[32m+[m[32m    STRATEGY_SIGNAL_GENERATED = "STRATEGY_SIGNAL_GENERATED"[m
     [m
[31m-[m
[1mdiff --git a/src/registry/strategy_models.py b/src/registry/strategy_models.py[m
[1mdeleted file mode 100644[m
[1mindex f583e31..0000000[m
[1m--- a/src/registry/strategy_models.py[m
[1m+++ /dev/null[m
[36m@@ -1,26 +0,0 @@[m
[31m-from dataclasses import dataclass[m
[31m-[m
[31m-[m
[31m-@dataclass(frozen=True)[m
[31m-class StrategyGroup:[m
[31m-    """[m
[31m-    Identifies one unique strategy computation group.[m
[31m-[m
[31m-    Two groups are considered identical when all their[m
[31m-    configuration fields are identical.[m
[31m-    """[m
[31m-[m
[31m-    """[m
[31m-        StrategyGroup[m
[31m-        ([m
[31m-            strategy_type="EMA",[m
[31m-            symbol="NIFTY",[m
[31m-            timeframe="5m",[m
[31m-            parameters=(("period", 10),)[m
[31m-        )[m
[31m-    """[m
[31m-[m
[31m-    strategy_type: str[m
[31m-    symbol: str[m
[31m-    timeframe: str[m
[31m-    parameters: tuple[tuple[str, object], ...] = ()[m
\ No newline at end of file[m
[1mdiff --git a/src/registry/strategy_registry.py b/src/registry/strategy_registry.py[m
[1mindex f699ee2..3da2d38 100644[m
[1m--- a/src/registry/strategy_registry.py[m
[1m+++ b/src/registry/strategy_registry.py[m
[36m@@ -1,5 +1,4 @@[m
[31m-from .strategy_models import StrategyGroup[m
[31m-[m
[32m+[m[32mfrom strategy.strategy_models import StrategyGroup[m
 [m
 class StrategyRegistry:[m
     """[m
[36m@@ -16,15 +15,15 @@[m [mclass StrategyRegistry:[m
     def __init__(self) -> None:[m
         self._groups: set[StrategyGroup] = set()[m
 [m
[31m-    def add_strategy(self, group: StrategyGroup) -> None:[m
[32m+[m[32m    def add_group(self, group: StrategyGroup) -> None:[m
         """Register a strategy group."""[m
         self._groups.add(group)[m
 [m
[31m-    def remove_strategy(self, group: StrategyGroup) -> None:[m
[32m+[m[32m    def remove_group(self, group: StrategyGroup) -> None:[m
         """Remove a strategy group."""[m
         self._groups.discard(group)[m
 [m
[31m-    def get_strategies(self) -> set[StrategyGroup]:[m
[32m+[m[32m    def get_groups(self) -> set[StrategyGroup]:[m
         """Return a copy of all registered strategy groups."""[m
         return self._groups.copy()[m
 [m
[1mdiff --git a/src/session/session_manager.py b/src/session/session_manager.py[m
[1mindex 0010d7f..bef64e4 100644[m
[1m--- a/src/session/session_manager.py[m
[1m+++ b/src/session/session_manager.py[m
[36m@@ -2,7 +2,8 @@[m [mfrom event_system.event import Event[m
 from event_system.event_bus import EventBus[m
 from event_system.event_type import EventType[m
 [m
[31m-from registry.strategy_models import StrategyGroup[m
[32m+[m[32mfrom strategy.strategy_models import StrategyGroup[m
[32m+[m
 from session.user_session import UserSession[m
 from registry.subscription_registry import SubscriptionRegistry[m
 from registry.strategy_registry import StrategyRegistry[m
[36m@@ -122,7 +123,7 @@[m [mclass SessionManager:[m
 [m
             # Register unique strategy groups.[m
             for strategy in session.strategies:[m
[31m-                self._strategy_registry.add_strategy(strategy)[m
[32m+[m[32m                self._strategy_registry.add_group(strategy)[m
 [m
 [m
     def _clear_user_sessions(self) -> None:[m
[1mdiff --git a/src/session/user_session.py b/src/session/user_session.py[m
[1mindex ba718a8..92e6794 100644[m
[1m--- a/src/session/user_session.py[m
[1m+++ b/src/session/user_session.py[m
[36m@@ -1,5 +1,5 @@[m
 from dataclasses import dataclass, field[m
[31m-from registry.strategy_models import StrategyGroup[m
[32m+[m[32mfrom strategy.strategy_models import StrategyGroup[m
 [m
 @dataclass[m
 class UserSession:[m
[1mdiff --git a/tests/test_registry/test_strategy_registry.py b/tests/test_registry/test_strategy_registry.py[m
[1mindex 82154af..d5f5446 100644[m
[1m--- a/tests/test_registry/test_strategy_registry.py[m
[1m+++ b/tests/test_registry/test_strategy_registry.py[m
[36m@@ -1,4 +1,6 @@[m
[31m-from registry.strategy_models import StrategyGroup[m
[32m+[m
[32m+[m
[32m+[m[32mfrom strategy.strategy_models import StrategyGroup[m
 from registry.strategy_registry import StrategyRegistry[m
 [m
 [m
[36m@@ -12,9 +14,9 @@[m [mdef test_add_strategy():[m
         parameters=(("period", 10),)[m
     )[m
 [m
[31m-    registry.add_strategy(group)[m
[32m+[m[32m    registry.add_group(group)[m
 [m
[31m-    assert registry.get_strategies() == {group}[m
[32m+[m[32m    assert registry.get_groups() == {group}[m
 [m
 [m
 def test_add_multiple_strategies():[m
[36m@@ -34,10 +36,10 @@[m [mdef test_add_multiple_strategies():[m
         parameters=(("period", 10),)[m
     )[m
 [m
[31m-    registry.add_strategy(ema_nifty)[m
[31m-    registry.add_strategy(ema_reliance)[m
[32m+[m[32m    registry.add_group(ema_nifty)[m
[32m+[m[32m    registry.add_group(ema_reliance)[m
 [m
[31m-    assert registry.get_strategies() == {[m
[32m+[m[32m    assert registry.get_groups() == {[m
         ema_nifty,[m
         ema_reliance,[m
     }[m
[36m@@ -60,10 +62,10 @@[m [mdef test_duplicate_strategy_is_registered_only_once():[m
         parameters=(("period", 10),)[m
     )[m
 [m
[31m-    registry.add_strategy(group1)[m
[31m-    registry.add_strategy(group2)[m
[32m+[m[32m    registry.add_group(group1)[m
[32m+[m[32m    registry.add_group(group2)[m
 [m
[31m-    assert len(registry.get_strategies()) == 1[m
[32m+[m[32m    assert len(registry.get_groups()) == 1[m
 [m
 [m
 def test_different_parameters_create_different_groups():[m
[36m@@ -83,10 +85,10 @@[m [mdef test_different_parameters_create_different_groups():[m
         parameters=(("period", 20),)[m
     )[m
 [m
[31m-    registry.add_strategy(ema_10)[m
[31m-    registry.add_strategy(ema_20)[m
[32m+[m[32m    registry.add_group(ema_10)[m
[32m+[m[32m    registry.add_group(ema_20)[m
 [m
[31m-    assert len(registry.get_strategies()) == 2[m
[32m+[m[32m    assert len(registry.get_groups()) == 2[m
 [m
 [m
 def test_remove_strategy():[m
[36m@@ -99,10 +101,10 @@[m [mdef test_remove_strategy():[m
         parameters=(("period", 10),)[m
     )[m
 [m
[31m-    registry.add_strategy(group)[m
[31m-    registry.remove_strategy(group)[m
[32m+[m[32m    registry.add_group(group)[m
[32m+[m[32m    registry.remove_group(group)[m
 [m
[31m-    assert registry.get_strategies() == set()[m
[32m+[m[32m    assert registry.get_groups() == set()[m
 [m
 [m
 def test_remove_non_existing_strategy():[m
[36m@@ -115,9 +117,9 @@[m [mdef test_remove_non_existing_strategy():[m
         parameters=(("period", 10),)[m
     )[m
 [m
[31m-    registry.remove_strategy(group)[m
[32m+[m[32m    registry.remove_group(group)[m
 [m
[31m-    assert registry.get_strategies() == set()[m
[32m+[m[32m    assert registry.get_groups() == set()[m
 [m
 [m
 def test_get_strategies_returns_copy():[m
[36m@@ -130,9 +132,9 @@[m [mdef test_get_strategies_returns_copy():[m
         parameters=(("period", 10),)[m
     )[m
 [m
[31m-    registry.add_strategy(group)[m
[32m+[m[32m    registry.add_group(group)[m
 [m
[31m-    strategies = registry.get_strategies()[m
[31m-    strategies.clear()[m
[32m+[m[32m    groups = registry.get_groups()[m
[32m+[m[32m    groups.clear()[m
 [m
[31m-    assert registry.get_strategies() == {group}[m
\ No newline at end of file[m
[32m+[m[32m    assert registry.get_groups() == {group}[m
\ No newline at end of file[m
[1mdiff --git a/tests/test_session/test_session_manager.py b/tests/test_session/test_session_manager.py[m
[1mindex 3fea0a6..1aea7df 100644[m
[1m--- a/tests/test_session/test_session_manager.py[m
[1m+++ b/tests/test_session/test_session_manager.py[m
[36m@@ -3,6 +3,7 @@[m [mfrom event_system.event_bus import EventBus[m
 from event_system.event_type import EventType[m
 from session.session_manager import SessionManager[m
 from registry.subscription_registry import SubscriptionRegistry[m
[32m+[m[32m#from registry.strategy_registry import StrategyRegistry[m
 from registry.strategy_registry import StrategyRegistry[m
 [m
 [m
[36m@@ -96,7 +97,7 @@[m [mdef test_market_open_populates_strategy_registry():[m
     )[m
 [m
     # Assert[m
[31m-    strategies = strategy_registry.get_strategies()[m
[32m+[m[32m    strategies = strategy_registry.get_groups()[m
 [m
     assert len(strategies) == 3[m
 [m
