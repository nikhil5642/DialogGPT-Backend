import stripe
from server.fastApi.modules.databaseManagement import get_subscription_id, handle_subscription_creation, handle_subscription_deletion, handle_subscription_update
from src.DataBaseConstants import CUSTOMER, STATUS, SUBSCRIPTION, SUBSCRIPTION_ID,USER_ID,PLAN_ID,PRO_PLAN,ESSENTIALS_PLAN,ID
import requests
stripe.api_key="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"

SUBSCRIPTION_PRO= "price_1NlcebSBubjVCHLvON7VCorm"
SUBSCRIPTION_ESSENTIALS= "price_1NlcOLSBubjVCHLvMvpS6tnn" 
STRIPE_WEBHOOK_SECRET="whsec_rPIhd8WwG8gFqW5IctFOVcMB7Gxmd2kj" 
CURRENCY_LAYER_API_KEY="cf717babe6b5b06c2d88c673cf345864"
WEBSITE_BASE_URL="https://api.dialggpt.io"

def getPriceId(plan_id):
    if (plan_id==PRO_PLAN):
        return SUBSCRIPTION_PRO
    else:
        return SUBSCRIPTION_ESSENTIALS

def createStripeCheckoutSession(user_id,plan_id):
    price_id=getPriceId(plan_id)    
    old_subscription_id=get_subscription_id(user_id)
    if old_subscription_id and old_subscription_id.strip():
        try:
            if(plan_id==PRO_PLAN):
                name="Upgrade to Pro Plan!"
            else:
                name="Get started with essentials"
            session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[calculate_proration_item(old_subscription_id, price_id, name)],
            mode='payment',
            success_url=WEBSITE_BASE_URL + '/my-chatbots', 
            cancel_url=WEBSITE_BASE_URL + '/pricing',
            metadata={
                USER_ID: user_id,
                PLAN_ID: plan_id,
                SUBSCRIPTION_ID: old_subscription_id,
                }
            )
        except:
            session = create_new_subscription_checkout_session(user_id,plan_id,price_id)
        return session.id
    else:        
        session = create_new_subscription_checkout_session(user_id,plan_id,price_id)
        return session.id


def calculate_proration_item(subscription_id, new_price_id, name):
     
    # Retrieve the user's existing subscription
    subscription = stripe.Subscription.retrieve(subscription_id)
    
    # Simulate an invoice to calculate the proration
    items_to_modify = [{'id': item.id, 'deleted': True} for item in subscription['items']['data']]

    # Then, add the new item
    new_item = {
        'price': new_price_id,
    }
    items_to_modify.append(new_item)

    invoice = stripe.Invoice.upcoming(
        customer=subscription.customer,
        subscription=subscription.id,
        subscription_items=items_to_modify,
        subscription_proration_behavior='none'
    )

   
    current_amount = subscription['items']['data'][0].plan.amount  # Consider only the first item
    current_currency = subscription['items']['data'][0].plan.currency

    # Check if the currencies match
    if current_currency != invoice.currency:
        current_amount=get_converted_amount(current_amount, current_currency, invoice.currency)
       
    prorated_amount =  max(0,invoice.total - current_amount)
    
    return {
        "price_data": {
            "currency": invoice.currency,
            "unit_amount":prorated_amount,  
            "product_data": {
                'name': name,
            },
        },
        'quantity': 1,
    }



def get_conversion_rate(original_currency, target_currency):
    url = f"http://api.currencylayer.com/live?access_key={CURRENCY_LAYER_API_KEY}&currencies={original_currency},{target_currency}"
    response = requests.get(url)
    data = response.json()

    if not data['success']:
        raise Exception("API request failed:", data['error']['info'])
    
    return data['quotes'][f"{original_currency.upper()}{target_currency.upper()}"]

def get_converted_amount(amount, original_currency, target_currency):
    conversion_rate = get_conversion_rate( original_currency, target_currency)
    return int(amount * conversion_rate)


def create_new_subscription_checkout_session(user_id,plan_id,price_id):
    return stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=WEBSITE_BASE_URL+'/my-chatbots', 
            cancel_url=WEBSITE_BASE_URL+'/pricing',
            metadata=generateNewMetaData(user_id,plan_id)
        )



def manageWebhook(payload,sig_header):
    event = None
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        # Invalid payload
        return {STATUS: "invalid payload"}
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return {STATUS: "invalid signature"}
    
    data = event.data.object
    
    # Handle the event

    if event.type == 'checkout.session.completed':
        if(data[SUBSCRIPTION]):
            handle_subscription_creation(data.metadata[USER_ID],data[STATUS],data.metadata[PLAN_ID],data[SUBSCRIPTION],getMessageLimitAsPerPlan(data.metadata[PLAN_ID]))  
            add_metadata_to_subscription(data[SUBSCRIPTION],data.metadata) 
        elif SUBSCRIPTION_ID in data.metadata:
            handle_subscription_change(data.metadata[USER_ID],data[STATUS],data.metadata[PLAN_ID],data.metadata[SUBSCRIPTION_ID],getMessageLimitAsPerPlan(data.metadata[PLAN_ID]))  
    elif event.type == 'customer.subscription.updated':
        if USER_ID in data.metadata:
            handle_subscription_update(data.metadata[USER_ID],data[STATUS],data.metadata[PLAN_ID])
    elif event.type == 'customer.subscription.deleted':
        handle_subscription_deletion(data[ID])    

    return {STATUS: "success"}


def handle_subscription_change(user_id,subscription_status,plan_id,subscription_id,message_limit):
    subscription = stripe.Subscription.retrieve(subscription_id) 
    # Update the subscription to the new plan
    new_items = [{
            'id': subscription['items']['data'][0].id,
            'price': getPriceId(plan_id),
        }]
    for item in subscription['items']['data'][1:]:
        new_items.append({
            'id': item.id,
            'deleted': True
        })
    stripe.Subscription.modify(
        subscription_id,
        items=new_items,
        proration_behavior='none',  # Since we've already handled proration in the checkout session
    )
    handle_subscription_creation(user_id,subscription_status,plan_id,subscription_id,message_limit)  
    add_metadata_to_subscription(subscription_id,generateNewMetaData(user_id,plan_id)) 

def generateNewMetaData(user_id,plan_id):
    return {USER_ID: user_id,PLAN_ID:plan_id}

def getMessageLimitAsPerPlan(plan):
    if plan==PRO_PLAN:
        return 10000
    elif plan==ESSENTIALS_PLAN:
        return 2000
    else:
        return 30


def add_metadata_to_subscription(subscription_id, metadata):
    """
    Add metadata to a Stripe subscription.
    """
    stripe.Subscription.modify(subscription_id, metadata=metadata)
