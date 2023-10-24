from fastapi import HTTPException
import stripe
from server.fastApi.modules.databaseManagement import (
    get_subscription_id,
    get_subscription_plan,
    handle_subscription_creation,
    handle_subscription_deletion,
    handle_subscription_update,
    to_camel_case,
)
from src.DataBaseConstants import (
    BASIC_PLAN,
    CUSTOMER,
    FREE_PLAN,
    STATUS,
    SUBSCRIPTION,
    SUBSCRIPTION_ID,
    USER_ID,
    PLAN_ID,
    PRO_PLAN,
    ESSENTIALS_PLAN,
    ID,
)
import requests
from src.scripts.chatbotUtils import getMessageLimitAsPerPlan
import time

stripe.api_key = "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"

SUBSCRIPTION_PRO = "price_1NmOk6SBubjVCHLvylBtaAiJ"
SUBSCRIPTION_ESSENTIALS = "price_1NyDl5SBubjVCHLvz21h4vso"
SUBSCRIPTION_BASIC = "price_1NyDofSBubjVCHLvdGoxWpyU"
STRIPE_WEBHOOK_SECRET = "whsec_rPIhd8WwG8gFqW5IctFOVcMB7Gxmd2kj"
CURRENCY_LAYER_API_KEY = "cf717babe6b5b06c2d88c673cf345864"
WEBSITE_BASE_URL = "https://dialoggpt.io"

# --------------------------------------------------------------------------------------------
# Test Keys
# stripe.api_key="sk_test_51NlWuWSBubjVCHLvXTVthdf3CsRtD7tCSGXjvzzPDOeCzLg9N8bZfcDAw1NW0VjjxiM1R6acM6grcYdODRETSaLJ007kodrpRe"

# SUBSCRIPTION_PRO= "price_1Nz3BMSBubjVCHLv7zWrqlcv"
# SUBSCRIPTION_ESSENTIALS= "price_1Nz3LhSBubjVCHLvxBZAB2Zm"
# SUBSCRIPTION_BASIC="price_1NypwASBubjVCHLv1vdbTuNu"
# STRIPE_WEBHOOK_SECRET="whsec_u1mQ0SXb8IJ0k0XWPhQ1nMW6mXHLA4yi"
# CURRENCY_LAYER_API_KEY="cf717babe6b5b06c2d88c673cf345864"
# WEBSITE_BASE_URL="http://localhost:3000"

# --------------------------------------------------------------------------------------------


def getPriceId(plan_id):
    if plan_id == PRO_PLAN:
        return SUBSCRIPTION_PRO
    elif plan_id == ESSENTIALS_PLAN:
        return SUBSCRIPTION_ESSENTIALS
    else:
        return SUBSCRIPTION_BASIC


def createStripeCheckoutSession(user_id, plan_id):
    price_id = getPriceId(plan_id)
    old_subscription_id = get_subscription_id(user_id)
    old_subscription_plan = get_subscription_plan(user_id)

    if old_subscription_id and old_subscription_id.strip():
        try:
            if old_subscription_plan == plan_id:
                raise Exception("Already subscribed to this plan")
            if old_subscription_plan == plan_id:
                name = "Stay on the same plan!"
            elif old_subscription_plan == FREE_PLAN:
                name = "Upgrade to Pro" + to_camel_case(plan_id) + " Plan!"
            elif old_subscription_plan == BASIC_PLAN:
                name = "Upgrade to " + to_camel_case(plan_id) + " Plan!"
            elif old_subscription_plan == ESSENTIALS_PLAN:
                if plan_id == PRO_PLAN:
                    name = "Upgrade to Pro Plan!"
                else:
                    name = "Downgrade to Basic Plan!"
            else:
                name = "Downgrade to " + to_camel_case(plan_id) + " Plan!"

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    calculate_proration_item(old_subscription_id, price_id, name)
                ],
                mode="payment",
                allow_promotion_codes=True,
                success_url=WEBSITE_BASE_URL + "/my-chatbots",
                cancel_url=WEBSITE_BASE_URL + "/pricing",
                metadata={
                    USER_ID: user_id,
                    PLAN_ID: plan_id,
                    SUBSCRIPTION_ID: old_subscription_id,
                },
            )
        except:
            session = create_new_subscription_checkout_session(
                user_id, plan_id, price_id
            )
        return session.id
    else:
        session = create_new_subscription_checkout_session(user_id, plan_id, price_id)
        return session.id


def calculate_proration_item(subscription_id, new_price_id, name):
    # Retrieve the user's existing subscription
    subscription = stripe.Subscription.retrieve(subscription_id)

    # Check if the subscription is still under a free trial
    is_under_trial = subscription.trial_end and subscription.trial_end > time.time()

    # Simulate an invoice to calculate the proration
    items_to_modify = [
        {"id": item.id, "deleted": True} for item in subscription["items"]["data"]
    ]

    # Then, add the new item
    new_item = {
        "price": new_price_id,
    }
    items_to_modify.append(new_item)

    invoice = stripe.Invoice.upcoming(
        customer=subscription.customer,
        subscription=subscription.id,
        subscription_items=items_to_modify,
        subscription_proration_behavior="none",
    )

    current_amount = subscription["items"]["data"][
        0
    ].plan.amount  # Consider only the first item
    current_currency = subscription["items"]["data"][0].plan.currency

    # Check if the currencies match
    if current_currency != invoice.currency:
        current_amount = get_converted_amount(
            current_amount, current_currency, invoice.currency
        )

    if is_under_trial:
        prorated_amount = invoice.total
    else:
        prorated_amount = max(0, invoice.total - current_amount)
    return {
        "price_data": {
            "currency": invoice.currency,
            "unit_amount": prorated_amount,
            "product_data": {
                "name": name,
            },
        },
        "quantity": 1,
    }


def get_conversion_rate(original_currency, target_currency):
    url = f"http://api.currencylayer.com/live?access_key={CURRENCY_LAYER_API_KEY}&currencies={original_currency},{target_currency}"
    response = requests.get(url)
    data = response.json()

    if not data["success"]:
        raise Exception("API request failed:", data["error"]["info"])

    return data["quotes"][f"{original_currency.upper()}{target_currency.upper()}"]


def get_converted_amount(amount, original_currency, target_currency):
    conversion_rate = get_conversion_rate(original_currency, target_currency)
    return int(amount * conversion_rate)


def create_new_subscription_checkout_session(user_id, plan_id, price_id):
    subscription_data = {"trial_period_days": 7} if "basic" in plan_id.lower() else {}
    return stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        mode="subscription",
        allow_promotion_codes=True,
        success_url=WEBSITE_BASE_URL + "/my-chatbots",
        cancel_url=WEBSITE_BASE_URL + "/pricing",
        metadata=generateNewMetaData(user_id, plan_id),
        subscription_data=subscription_data,
    )


def manageWebhook(payload, sig_header):
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid Payload")
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invlaid Signature")

    data = event.data.object

    if event.type == "checkout.session.completed":
        if SUBSCRIPTION_ID in data.metadata:
            handle_subscription_change(
                data.metadata[USER_ID],
                data[STATUS],
                data.metadata[PLAN_ID],
                data.metadata[SUBSCRIPTION_ID],
                getMessageLimitAsPerPlan(data.metadata[PLAN_ID]),
            )
        elif data[SUBSCRIPTION]:
            handle_subscription_creation(
                data.metadata[USER_ID],
                data[STATUS],
                data.metadata[PLAN_ID],
                data[SUBSCRIPTION],
                getMessageLimitAsPerPlan(data.metadata[PLAN_ID]),
            )
            add_metadata_to_subscription(data[SUBSCRIPTION], data.metadata)
    elif event.type == "customer.subscription.updated":
        if USER_ID in data.metadata:
            handle_subscription_update(
                data.metadata[USER_ID],
                data[STATUS],
                data.metadata[PLAN_ID],
                getMessageLimitAsPerPlan(data.metadata[PLAN_ID]),
            )
    elif event.type == "customer.subscription.deleted":
        handle_subscription_deletion(data[ID])

    return {STATUS: "success"}


def handle_subscription_change(
    user_id, subscription_status, plan_id, subscription_id, message_limit
):
    subscription = stripe.Subscription.retrieve(subscription_id)
    # Update the subscription to the new plan
    new_items = [
        {
            "id": subscription["items"]["data"][0].id,
            "price": getPriceId(plan_id),
        }
    ]
    for item in subscription["items"]["data"][1:]:
        new_items.append({"id": item.id, "deleted": True})
    stripe.Subscription.modify(
        subscription_id,
        items=new_items,
        proration_behavior="none",  # Since we've already handled proration in the checkout session
    )
    handle_subscription_creation(
        user_id, subscription_status, plan_id, subscription_id, message_limit
    )
    add_metadata_to_subscription(subscription_id, generateNewMetaData(user_id, plan_id))


def generateNewMetaData(user_id, plan_id):
    return {USER_ID: user_id, PLAN_ID: plan_id}


def add_metadata_to_subscription(subscription_id, metadata):
    """
    Add metadata to a Stripe subscription.
    """
    stripe.Subscription.modify(subscription_id, metadata=metadata)


def subscription_management_url(user_id):
    old_subscription_id = get_subscription_id(user_id)
    # Fetch the subscription to get the customer ID
    subscription = stripe.Subscription.retrieve(old_subscription_id)
    customer_id = subscription.customer
    # Create a session for the Stripe Customer Portal
    session = stripe.billing_portal.Session.create(
        customer=customer_id, return_url=WEBSITE_BASE_URL + "/pricing"
    )
    return session.url
