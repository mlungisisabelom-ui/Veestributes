"""
Payment Processing Module
Handles payment processing using Stripe for music distribution services.
"""

import os
import logging
import stripe
from flask import current_app, jsonify
from datetime import datetime

logger = logging.getLogger(__name__)

class PaymentProcessor:
    """Handles payment processing operations."""

    def __init__(self, stripe_secret_key=None):
        self.stripe_secret_key = stripe_secret_key or os.getenv('STRIPE_SECRET_KEY')
        if self.stripe_secret_key:
            stripe.api_key = self.stripe_secret_key
        else:
            logger.warning("Stripe secret key not configured")

    def create_payment_intent(self, amount, currency='usd', metadata=None):
        """
        Create a Stripe PaymentIntent for processing payments.

        Args:
            amount (int): Amount in cents
            currency (str): Currency code
            metadata (dict): Additional metadata

        Returns:
            dict: PaymentIntent data
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                metadata=metadata or {},
                automatic_payment_methods={
                    'enabled': True,
                },
            )

            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
                'amount': amount,
                'currency': currency
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe PaymentIntent creation failed: {str(e)}")
            raise

    def create_checkout_session(self, items, success_url, cancel_url, customer_email=None):
        """
        Create a Stripe Checkout Session for subscription or one-time payments.

        Args:
            items (list): List of items to purchase
            success_url (str): URL to redirect on success
            cancel_url (str): URL to redirect on cancel
            customer_email (str): Customer email

        Returns:
            dict: Checkout session data
        """
        try:
            session_data = {
                'payment_method_types': ['card'],
                'line_items': items,
                'mode': 'payment',
                'success_url': success_url,
                'cancel_url': cancel_url,
            }

            if customer_email:
                session_data['customer_email'] = customer_email

            session = stripe.checkout.Session.create(**session_data)

            return {
                'session_id': session.id,
                'url': session.url
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe Checkout session creation failed: {str(e)}")
            raise

    def create_subscription(self, customer_id, price_id, metadata=None):
        """
        Create a subscription for recurring payments.

        Args:
            customer_id (str): Stripe customer ID
            price_id (str): Stripe price ID
            metadata (dict): Additional metadata

        Returns:
            dict: Subscription data
        """
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{
                    'price': price_id,
                }],
                metadata=metadata or {},
            )

            return {
                'subscription_id': subscription.id,
                'status': subscription.status,
                'current_period_end': subscription.current_period_end
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription creation failed: {str(e)}")
            raise

    def create_customer(self, email, name=None, metadata=None):
        """
        Create a Stripe customer.

        Args:
            email (str): Customer email
            name (str): Customer name
            metadata (dict): Additional metadata

        Returns:
            dict: Customer data
        """
        try:
            customer_data = {
                'email': email,
                'metadata': metadata or {}
            }

            if name:
                customer_data['name'] = name

            customer = stripe.Customer.create(**customer_data)

            return {
                'customer_id': customer.id,
                'email': customer.email,
                'name': customer.name
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {str(e)}")
            raise

    def retrieve_payment_intent(self, payment_intent_id):
        """
        Retrieve a PaymentIntent by ID.

        Args:
            payment_intent_id (str): PaymentIntent ID

        Returns:
            dict: PaymentIntent data
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            return {
                'id': intent.id,
                'status': intent.status,
                'amount': intent.amount,
                'currency': intent.currency,
                'metadata': intent.metadata
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve PaymentIntent {payment_intent_id}: {str(e)}")
            raise

    def handle_webhook(self, payload, sig_header, endpoint_secret):
        """
        Handle Stripe webhook events.

        Args:
            payload (bytes): Raw webhook payload
            sig_header (str): Stripe signature header
            endpoint_secret (str): Webhook endpoint secret

        Returns:
            dict: Event data
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )

            # Handle different event types
            event_data = {
                'type': event.type,
                'data': event.data.object,
                'created': datetime.fromtimestamp(event.created)
            }

            logger.info(f"Received Stripe webhook: {event.type}")

            return event_data

        except ValueError as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            raise ValueError("Invalid signature")

    def refund_payment(self, payment_intent_id, amount=None, reason='requested_by_customer'):
        """
        Refund a payment.

        Args:
            payment_intent_id (str): PaymentIntent ID to refund
            amount (int): Amount to refund in cents (full refund if None)
            reason (str): Reason for refund

        Returns:
            dict: Refund data
        """
        try:
            refund_data = {
                'payment_intent': payment_intent_id,
                'reason': reason
            }

            if amount:
                refund_data['amount'] = amount

            refund = stripe.Refund.create(**refund_data)

            return {
                'refund_id': refund.id,
                'status': refund.status,
                'amount': refund.amount
            }

        except stripe.error.StripeError as e:
            logger.error(f"Refund failed for {payment_intent_id}: {str(e)}")
            raise

# Pricing configurations
PRICING_PLANS = {
    'single_release': {
        'name': 'Single Release',
        'price': 1999,  # $19.99 in cents
        'currency': 'usd',
        'description': 'Distribute one track to all platforms'
    },
    'album_release': {
        'name': 'Album Release',
        'price': 2999,  # $29.99 in cents
        'currency': 'usd',
        'description': 'Distribute up to 10 tracks to all platforms'
    },
    'unlimited_plan': {
        'name': 'Unlimited Plan',
        'price': 4999,  # $49.99 in cents
        'currency': 'usd',
        'interval': 'year',
        'description': 'Unlimited releases for one year'
    }
}

# Global payment processor instance
payment_processor = PaymentProcessor()
