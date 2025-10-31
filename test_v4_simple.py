"""
Simplified test for SPIN Training Bot v4 payment module.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("SPIN Training Bot v4 - Simple Module Test")
print("=" * 60)
print()

# Test imports
print("✓ Test 1: Importing modules...")
try:
    from database import init_db, close_db
    from database.models import SubscriptionType, PromocodeType
    from modules.payments import (
        TARIFFS, check_access, create_subscription,
        create_promocode, activate_promocode
    )
    from modules.payments.config import format_price
    print("  ✅ All modules imported successfully\n")
except Exception as e:
    print(f"  ❌ Import failed: {e}\n")
    sys.exit(1)

# Test configuration
print("✓ Test 2: Configuration...")
try:
    assert len(TARIFFS) == 6
    assert format_price('month') == "990 ₽"
    assert format_price('year') == "6990 ₽"
    print(f"  ✅ Tariffs: {len(TARIFFS)}")
    print(f"  ✅ Month: {format_price('month')}")
    print(f"  ✅ Year: {format_price('year')}\n")
except Exception as e:
    print(f"  ❌ Configuration test failed: {e}\n")
    sys.exit(1)

# Test database
print("✓ Test 3: Database initialization...")
try:
    os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test_v4_simple.db'

    async def test_db():
        await init_db()

    asyncio.run(test_db())
    print("  ✅ Database initialized\n")
except Exception as e:
    print(f"  ❌ Database init failed: {e}\n")
    sys.exit(1)

# Test subscription creation
print("✓ Test 4: Subscription system...")
try:
    async def test_subscription():
        from database import get_session
        session = await anext(get_session())

        try:
            # Create subscription
            await create_subscription(
                telegram_id=111222333,
                subscription_type=SubscriptionType.MONTH,
                duration_days=30,
                session=session
            )

            # Check access
            access = await check_access(111222333, session)

            assert access['has_access'] == True
            assert access['access_type'] == 'subscription'

            return access
        finally:
            await session.close()

    access_info = asyncio.run(test_subscription())
    print(f"  ✅ Subscription created")
    print(f"  ✅ Access check passed")
    print(f"     - Has access: {access_info['has_access']}")
    print(f"     - Type: {access_info['access_type']}\n")
except Exception as e:
    print(f"  ❌ Subscription test failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test promocodes
print("✓ Test 5: Promocode system...")
try:
    async def test_promocodes():
        from database import get_session
        session = await anext(get_session())

        try:
            # Create promocode
            success, msg, promo = await create_promocode(
                code="HELLO2024",
                promo_type=PromocodeType.TRAININGS,
                value=5,
                max_uses=50,
                expires_days=30,
                session=session
            )

            assert success == True

            # Activate promocode
            success2, msg2 = await activate_promocode(
                "HELLO2024",
                444555666,
                session
            )

            assert success2 == True

            # Check access after promo
            access = await check_access(444555666, session)
            assert access['has_access'] == True
            assert access['access_type'] == 'free_trainings'

            return promo, access
        finally:
            await session.close()

    promo, access = asyncio.run(test_promocodes())
    print(f"  ✅ Promocode created: {promo.code}")
    print(f"  ✅ Promocode activated")
    print(f"  ✅ Access granted")
    print(f"     - Trainings left: {access['details']['trainings_left']}\n")
except Exception as e:
    print(f"  ❌ Promocode test failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test payment providers
print("✓ Test 6: Payment providers...")
try:
    from modules.payments.providers import (
        YooKassaProvider, CloudPaymentsProvider,
        ProdamusProvider, get_payment_provider
    )

    providers = [
        YooKassaProvider(),
        CloudPaymentsProvider(),
        ProdamusProvider()
    ]

    for p in providers:
        name = p.get_provider_name()
        print(f"  ✅ {name.capitalize()} provider loaded")

    provider = get_payment_provider('yookassa')
    assert provider is not None
    print(f"  ✅ Provider factory works\n")
except Exception as e:
    print(f"  ❌ Providers test failed: {e}\n")
    sys.exit(1)

# Test messages & keyboards
print("✓ Test 7: UI components...")
try:
    from modules.payments.messages import WELCOME_SALES, TARIFF_MONTH
    from modules.payments.keyboards import (
        get_payment_menu_keyboard,
        get_tariffs_keyboard
    )

    assert len(WELCOME_SALES) > 100
    assert len(TARIFF_MONTH) > 50

    menu_kb = get_payment_menu_keyboard()
    tariffs_kb = get_tariffs_keyboard()

    assert menu_kb is not None
    assert tariffs_kb is not None

    print(f"  ✅ Messages loaded ({len(WELCOME_SALES)} chars)")
    print(f"  ✅ Keyboards generated\n")
except Exception as e:
    print(f"  ❌ UI components test failed: {e}\n")
    sys.exit(1)

# Cleanup
print("✓ Cleanup...")
try:
    asyncio.run(close_db())
    print("  ✅ Database closed\n")
except Exception as e:
    print(f"  ⚠️  Cleanup warning: {e}\n")

print("=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print()
print("Summary:")
print("  [✓] Module imports")
print("  [✓] Configuration (6 tariffs)")
print("  [✓] Database initialization")
print("  [✓] Subscription system")
print("  [✓] Promocode system")
print("  [✓] Payment providers (3)")
print("  [✓] UI components")
print()
print("🎉 The v4 payment module is fully functional!")
print()
print("Next steps:")
print("  1. Read V4_INTEGRATION_GUIDE.md")
print("  2. Integrate into bot.py")
print("  3. Test with real bot")
print()
