import json
from datetime import datetime
from typing import Optional, Dict, TYPE_CHECKING
from .const import TRANSACTION_SETTLED, DEFAULT_LIMIT, DEFAULT_PAGE_SIZE

if TYPE_CHECKING:
    from .client import Client
    from .list import PaginatedList


class ModelBase:
    """Base class for all models."""

    def __init__(self, client: "Client", data: Dict):
        self._client = client
        self.raw = data


class Transaction(ModelBase):
    """Representation of a transaction

    id: the unique id of the transaction
    status: either "HELD" or "SETTLED"
    pending: whether the transaction has been settled
    raw_text:
    description: typically the merchant/account
    message: typically the message/description
    settled_at:
    created_at:
    amount:
    currency:
    raw: the raw serialised data from the api
    """

    def __init__(self, client: "Client", data):
        super().__init__(client, data)
        self.id: str = data["id"]

        attributes = data["attributes"]

        self.status: str = attributes["status"]
        self.pending: bool = self.status != TRANSACTION_SETTLED
        self.raw_text: Optional[str] = attributes["rawText"]
        self.description: str = attributes["description"]
        self.message: Optional[str] = attributes["message"]
        self.settled_at: Optional[datetime] = (
            datetime.fromisoformat(attributes["settledAt"])
            if attributes["settledAt"]
            else None
        )
        self.created_at: datetime = datetime.fromisoformat(attributes["createdAt"])
        self.amount: float = float(attributes["amount"]["value"])
        self.currency: str = attributes["amount"]["currencyCode"]

        relationships = data["relationships"]

        self.category: Optional[str] = (
            relationships["category"]["data"]["id"]
            if relationships["category"]["data"]
            else None
        )
        self.parentCategory: Optional[str] = (
            relationships["parentCategory"]["data"]["id"]
            if relationships["parentCategory"]["data"]
            else None
        )
        self.tags: List[str] = [
            tag["id"] for tag in relationships["tags"]["data"]
        ]

    def format_desc(self):
        """Returns a formatted description using the transactions description and message."""
        if self.message:
            return f"{self.description}: {self.message}"
        return f"{self.description}"

    def __repr__(self) -> str:
        """Return the representation of the transaction."""
        return f"<Transaction {self.status}: {self.amount} {self.currency} [{self.description}]>"


class Account(ModelBase):
    """Representation of a transaction

    id: the unique id of the account
    type: either "TRANSACTIONAL" or "SAVER"
    name: the name of the account
    balance: amount of available funds
    currency:
    created_at: date and time the account was created
    raw: the raw serialised data from the api
    """

    def __init__(self, client: "Client", data: Dict):
        super().__init__(client, data)
        self.id: str = data["id"]

        attributes = data["attributes"]

        self.name: str = attributes["displayName"]
        self.type: str = attributes["accountType"]
        self.created_at: datetime = datetime.fromisoformat(attributes["createdAt"])
        self.balance: float = float(attributes["balance"]["value"])
        self.currency: str = attributes["balance"]["currencyCode"]

    def transactions(
        self,
        limit: Optional[int] = DEFAULT_LIMIT,
        page_size: int = DEFAULT_PAGE_SIZE,
        status: str = None,
        since: datetime = None,
        until: datetime = None,
        category: str = None,
        tag: str = None,
    ) -> "PaginatedList[Transaction]":
        """Returns the transactions for this account.

        :param limit maximum number of records to return (set to None for all transactions)
        :param page_size number of records to fetch in each request (max 100)
        :param status:
        :param since:
        :param until:
        :param category:
        :param tag:
        """
        return self._client.transactions(
            limit=limit,
            page_size=page_size,
            status=status,
            since=since,
            until=until,
            category=category,
            tag=tag,
            account_id=self.id,
        )

    def __repr__(self) -> str:
        """Return the representation of the account."""
        return f"<Account '{self.name}' ({self.type}): {self.balance} {self.currency}>"


class Webhook(ModelBase):
    """Representation of a webhook

    id: the unique id of the webhook
    url: the url of the webhook
    description: optional description of the webhook
    secret_key: key used to verify authenticity of webhook events
    created_at: date-time the webhook was created
    raw: the raw serialised data from the api
    """

    def __init__(self, client: "Client", data: Dict):
        super().__init__(client, data)
        self.id: str = data["id"]

        attributes = data["attributes"]

        self.url: str = attributes["url"]
        self.description: Optional[str] = attributes.get("description")
        self.secret_key: Optional[str] = attributes.get("secretKey")
        self.created_at: datetime = datetime.fromisoformat(attributes["createdAt"])

    def ping(self) -> "WebhookEvent":
        """Sends a ping event to the webhook"""
        return self._client.webhook.ping(self.id)

    def logs(
        self, limit: Optional[int] = DEFAULT_LIMIT, page_size: int = DEFAULT_PAGE_SIZE
    ) -> "PaginatedList[WebhookLog]":
        """Returns the logs of this webhook.

        :param limit maximum number of records to return (set to None for all transactions)
        :param page_size number of records to fetch in each request (max 100)
        """
        return self._client.webhook.logs(self.id, limit=limit, page_size=page_size)

    def delete(self):
        """Deletes the webhook."""
        return self._client.webhook.delete(self.id)

    def __repr__(self) -> str:
        """Return the representation of the webhook."""
        if self.description:
            return f"<Webhook '{self.id}': {self.url} ({self.description})>"
        return f"<Webhook '{self.id}': {self.url}>"


class WebhookLog(ModelBase):
    """Representation of a webhook log entry

    id: the unique id of the log entry
    event: the webhook event associated with the log
    response_code: response code from the receiver
    response_body: response body from the receiver
    delivery_status: whether the event has been delivered
    created_at: date-time the entry was created
    raw: the raw serialised data from the api
    """

    def __init__(self, client: "Client", data: Dict):
        super().__init__(client, data)
        self.id: str = data["id"]

        attributes = data["attributes"]

        self.event = WebhookEvent(
            self._client, json.loads(attributes["request"]["body"])["data"]
        )

        self.delivery_status: str = attributes["deliveryStatus"]
        self.created_at: datetime = datetime.fromisoformat(attributes["createdAt"])

        response = attributes["response"] or {}
        self.response_code: Optional[int] = response.get("statusCode")
        self.response_body: Optional[str] = response.get("body")

    def __repr__(self) -> str:
        """Return the representation of the webhook log."""
        if self.response_code:
            return f"<WebhookLog {self.delivery_status}: response_code={self.response_code}>"
        return f"<WebhookLog {self.delivery_status}>"


class WebhookEvent(ModelBase):
    """Representation of a webhook event

    id: the unique id of the event
    type: the event type
    webhook_id: the webhook id associated with this event
    transaction_id: the transaction id associated with this event
    created_at: date-time the event was created
    raw: the raw serialised data from the api
    """

    def __init__(self, client: "Client", data: Dict):
        super().__init__(client, data)
        self.id: str = data["id"]

        attributes = data["attributes"]

        self.type: str = attributes["eventType"]
        self.created_at: datetime = datetime.fromisoformat(attributes["createdAt"])

        relationships = data["relationships"]

        self.webhook_id: str = relationships["webhook"]["data"]["id"]
        self.transaction_id: Optional[str] = None

        if "transaction" in relationships:
            self.transaction_id = relationships["transaction"]["data"]["id"]

    def webhook(self) -> Webhook:
        """Fetch the details of the associated webhook."""
        return self._client.webhook(self.webhook_id)

    def transaction(self) -> Optional[Transaction]:
        """Fetch the details of the associated transaction."""
        if self.transaction_id:
            return self._client.transaction(self.transaction_id)

    def __repr__(self) -> str:
        """Return the representation of the webhook event."""
        if self.transaction_id:
            return f"<WebhookEvent {self.type}: webhook_id='{self.webhook_id}' transaction_id='{self.transaction_id}'>"
        return f"<WebhookEvent {self.type}: webhook_id='{self.webhook_id}'>"
