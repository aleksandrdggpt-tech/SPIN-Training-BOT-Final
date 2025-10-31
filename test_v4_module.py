"""
Test script for SPIN Training Bot v4 payment module.
Tests database, models, and payment logic without running the full bot.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("SPIN Training Bot v4 - Module Test")
print("=" * 60)
print()

# Test 1: Import modules
print("Test 1: Importing modules...")
try:
    from database import init_db, get_session, close_db
    from database.models import (
        User, Subscription, Payment, Promocode,
        PromocodeUsage, FreeTraining,
        SubscriptionType, PromocodeType, FreeTrainingSource
    )
    from modules.payments import (
        TARIFFS, subscription_required,
        check_access, create_subscription, create_promocode
    )
    from modules.payments.config import get_tariff, format_price
    from modules.payments.promocodes import validate_promocode, activate_promocode
    print("✅ All modules imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

print()

# Test 2: Database initialization
print("Test 2: Initializing test database...")
try:
    # Use test database
    os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test_spin_bot.db'

    async def test_db_init():
        await init_db()
        print("✅ Database initialized")

    asyncio.run(test_db_init())
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    sys.exit(1)

print()

# Test 3: Configuration
print("Test 3: Testing configuration...")
try:
    assert len(TARIFFS) == 6, "Expected 6 tariffs"

    month_tariff = get_tariff('month')
    assert month_tariff['price'] == 990, "Month tariff price should be 990"

    year_tariff = get_tariff('year')
    assert year_tariff['price'] == 6990, "Year tariff price should be 6990"

    price_str = format_price('month')
    assert price_str == "990 ₽", f"Expected '990 ₽', got '{price_str}'"

    print(f"✅ Configuration OK")
    print(f"   - Tariffs: {len(TARIFFS)}")
    print(f"   - Month: {format_price('month')}")
    print(f"   - Year: {format_price('year')}")
except Exception as e:
    print(f"❌ Configuration test failed: {e}")
    sys.exit(1)

print()

# Test 4: Database models
print("Test 4: Testing database models...")
try:
    async def test_models():
        session = await anext(get_session())
        try:
            # Create test user
            user = User(
                telegram_id=123456789,
                username="test_user",
                first_name="Test",
                total_trainings=0
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            print(f"✅ Created user: {user}")

            # Create subscription
            subscription = Subscription(
                user_id=user.id,
                subscription_type=SubscriptionType.MONTH,
                is_active=True
            )
            session.add(subscription)
            await session.commit()

            print(f"✅ Created subscription: {subscription}")

            # Create promocode
            promo = Promocode(
                code="TEST2024",
                type=PromocodeType.TRAININGS,
                value=5,
                max_uses=10,
                current_uses=0
            )
            session.add(promo)
            await session.commit()

            print(f"✅ Created promocode: {promo}")

            return user, subscription, promo
        finally:
            await session.close()

    asyncio.run(test_models())
except Exception as e:
    print(f"❌ Database models test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 5: Subscription logic
print("Test 5: Testing subscription logic...")
try:
    async def test_subscription_logic():
        from datetime import datetime, timedelta

        async with get_session() as session:
            # Create subscription programmatically
            await create_subscription(
                telegram_id=999888777,
                subscription_type=SubscriptionType.MONTH,
                duration_days=30,
                session=session
            )

            print("✅ Created subscription via API")

            # Check access
            access_info = await check_access(999888777, session)

            assert access_info['has_access'] == True, "User should have access"
            assert access_info['access_type'] == 'subscription', "Access type should be subscription"

            print(f"✅ Access check passed")
            print(f"   - Has access: {access_info['has_access']}")
            print(f"   - Access type: {access_info['access_type']}")
            print(f"   - Details: {access_info['details']}")

    asyncio.run(test_subscription_logic())
except Exception as e:
    print(f"❌ Subscription logic test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 6: Promocode system
print("Test 6: Testing promocode system...")
try:
    async def test_promocode_system():
        async with get_session() as session:
            # Create promocode
            success, message, promo = await create_promocode(
                code="WELCOME",
                promo_type=PromocodeType.TRAININGS,
                value=3,
                max_uses=100,
                expires_days=30,
                session=session
            )

            assert success == True, "Promocode creation should succeed"
            print(f"✅ Promocode created: {promo.code}")

            # Validate promocode
            validation = await validate_promocode("WELCOME", 111222333, session)
            assert validation['valid'] == True, "Promocode should be valid"

            print(f"✅ Promocode validation passed")

            # Activate promocode
            success, msg = await activate_promocode("WELCOME", 111222333, session)
            assert success == True, f"Activation should succeed: {msg}"

            print(f"✅ Promocode activated: {msg}")

            # Check access after activation
            access_info = await check_access(111222333, session)
            assert access_info['has_access'] == True, "User should have access after promo"
            assert access_info['access_type'] == 'free_trainings', "Access type should be free_trainings"

            print(f"✅ Access granted via promocode")
            print(f"   - Trainings left: {access_info['details']['trainings_left']}")

    asyncio.run(test_promocode_system())
except Exception as e:
    print(f"❌ Promocode system test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 7: Payment providers
print("Test 7: Testing payment providers...")
try:
    from modules.payments.providers import (
        PaymentProvider, YooKassaProvider,
        CloudPaymentsProvider, ProdamusProvider,
        get_payment_provider
    )

    # Test provider instantiation
    yookassa = YooKassaProvider()
    assert yookassa.get_provider_name() == 'yookassa'
    print(f"✅ YooKassa provider: {yookassa.get_provider_name()}")

    cloudpayments = CloudPaymentsProvider()
    assert cloudpayments.get_provider_name() == 'cloudpayments'
    print(f"✅ CloudPayments provider: {cloudpayments.get_provider_name()}")

    prodamus = ProdamusProvider()
    assert prodamus.get_provider_name() == 'prodamus'
    print(f"✅ Prodamus provider: {prodamus.get_provider_name()}")

    # Test factory
    provider = get_payment_provider('yookassa')
    assert isinstance(provider, YooKassaProvider)
    print(f"✅ Provider factory works")

except Exception as e:
    print(f"❌ Payment providers test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 8: Messages and keyboards
print("Test 8: Testing messages and keyboards...")
try:
    from modules.payments.messages import (
        WELCOME_SALES, TARIFF_MONTH, TARIFF_YEAR
    )
    from modules.payments.keyboards import (
        get_payment_menu_keyboard,
        get_tariffs_keyboard,
        get_free_access_keyboard
    )

    assert len(WELCOME_SALES) > 0, "Welcome message should not be empty"
    assert len(TARIFF_MONTH) > 0, "Month tariff message should not be empty"

    print(f"✅ Messages loaded (sample length: {len(WELCOME_SALES)})")

    # Test keyboards
    menu_kb = get_payment_menu_keyboard()
    assert menu_kb is not None, "Menu keyboard should be created"

    tariffs_kb = get_tariffs_keyboard()
    assert tariffs_kb is not None, "Tariffs keyboard should be created"

    print(f"✅ Keyboards generated")

except Exception as e:
    print(f"❌ Messages/keyboards test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Cleanup
print("Cleanup: Closing database...")
try:
    asyncio.run(close_db())
    print("✅ Database closed")
except Exception as e:
    print(f"⚠️  Cleanup warning: {e}")

print()
print("=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print()
print("Summary:")
print("  ✓ Module imports")
print("  ✓ Database initialization")
print("  ✓ Configuration")
print("  ✓ Database models")
print("  ✓ Subscription logic")
print("  ✓ Promocode system")
print("  ✓ Payment providers")
print("  ✓ Messages and keyboards")
print()
print("The v4 payment module is fully functional!")
print("Next step: Integrate into bot.py (see V4_INTEGRATION_GUIDE.md)")
print()
