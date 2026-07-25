"""
AlphaPass – DynamoDB Data Access Layer
All production routers use this module exclusively.
"""
import os
import uuid
import boto3
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.core.config import settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


class DynamoDBHelper:
    def __init__(self):
        self.region = settings.AWS_REGION
        self.resource = boto3.resource("dynamodb", region_name=self.region)

        # Table names from settings (populated from Lambda env vars)
        self.events_table_name            = settings.EVENTS_TABLE
        self.registrations_table_name     = settings.REGISTRATIONS_TABLE
        self.organizers_table_name        = settings.ORGANIZERS_TABLE
        self.admins_table_name            = settings.ADMINS_TABLE
        self.orders_table_name            = settings.ORDERS_TABLE
        self.tickets_table_name           = settings.TICKETS_TABLE
        self.promo_codes_table_name       = settings.PROMO_CODES_TABLE
        self.resale_listings_table_name   = settings.RESALE_LISTINGS_TABLE
        self.transfers_table_name         = settings.TRANSFERS_TABLE
        self.payouts_table_name           = settings.PAYOUTS_TABLE
        self.platform_settings_table_name = settings.PLATFORM_SETTINGS_TABLE
        self.audit_logs_table_name        = settings.AUDIT_LOGS_TABLE
        self.event_categories_table_name  = settings.EVENT_CATEGORIES_TABLE

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_table(self, table_name: str):
        return self.resource.Table(table_name)

    def _convert_floats(self, item: Any) -> Any:
        """Recursively convert float/Decimal/datetime values for DynamoDB storage."""
        if isinstance(item, list):
            return [self._convert_floats(x) for x in item]
        elif isinstance(item, dict):
            return {k: self._convert_floats(v) for k, v in item.items()}
        elif isinstance(item, float):
            return Decimal(str(item))
        elif isinstance(item, Decimal):
            return item
        elif isinstance(item, datetime):
            return item.isoformat()
        return item

    def _convert_decimals(self, item: Any) -> Any:
        """Recursively convert DynamoDB Decimal values back to Python types."""
        if isinstance(item, list):
            return [self._convert_decimals(x) for x in item]
        elif isinstance(item, dict):
            return {k: self._convert_decimals(v) for k, v in item.items()}
        elif isinstance(item, Decimal):
            return int(item) if item % 1 == 0 else float(item)
        return item

    def _scan_all(self, table_name: str, **kwargs) -> List[Dict[str, Any]]:
        """Full table scan with pagination."""
        table = self._get_table(table_name)
        response = table.scan(**kwargs)
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"], **kwargs)
            items.extend(response.get("Items", []))
        return self._convert_decimals(items)

    def _query_gsi(self, table_name: str, index_name: str, key_name: str, key_value: str) -> List[Dict[str, Any]]:
        """Query a GSI by exact key match."""
        from boto3.dynamodb.conditions import Key
        table = self._get_table(table_name)
        response = table.query(
            IndexName=index_name,
            KeyConditionExpression=Key(key_name).eq(key_value)
        )
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.query(
                IndexName=index_name,
                KeyConditionExpression=Key(key_name).eq(key_value),
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))
        return self._convert_decimals(items)

    def _build_update_expression(self, update_data: Dict[str, Any]):
        """Build a DynamoDB UpdateExpression from a dict."""
        update_data = self._convert_floats(update_data)
        parts = []
        names = {}
        values = {}
        for k, v in update_data.items():
            attr = f"#attr_{k}"
            val = f":val_{k}"
            parts.append(f"{attr} = {val}")
            names[attr] = k
            values[val] = v
        parts.append("#attr_updated_at = :val_updated_at")
        names["#attr_updated_at"] = "updated_at"
        values[":val_updated_at"] = _now_iso()
        return "SET " + ", ".join(parts), names, values

    # ── Admin Table API ───────────────────────────────────────────────────────

    def create_admin(self, admin_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.admins_table_name)
        item = {"AdminID": admin_id, **self._convert_floats(data), "created_at": _now_iso()}
        table.put_item(Item=item)
        return self._convert_decimals(item)

    def get_admin(self, admin_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.admins_table_name)
        response = table.get_item(Key={"AdminID": admin_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def get_admin_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        items = self._query_gsi(self.admins_table_name, "email-index", "email", email)
        return items[0] if items else None

    def update_admin(self, admin_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.admins_table_name)
        expr, names, values = self._build_update_expression(update_data)
        response = table.update_item(
            Key={"AdminID": admin_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW"
        )
        item = response.get("Attributes")
        return self._convert_decimals(item) if item else None

    def list_admins(self) -> List[Dict[str, Any]]:
        return self._scan_all(self.admins_table_name)

    def count_admins(self) -> int:
        table = self._get_table(self.admins_table_name)
        response = table.scan(Select="COUNT")
        return response.get("Count", 0)

    # ── Organizer Table API ───────────────────────────────────────────────────

    def create_organizer(self, organizer_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.organizers_table_name)
        item = {"OrganizerID": organizer_id, **self._convert_floats(data), "created_at": _now_iso()}
        table.put_item(Item=item)
        return self._convert_decimals(item)

    def get_organizer(self, organizer_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.organizers_table_name)
        response = table.get_item(Key={"OrganizerID": organizer_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def get_organizer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        items = self._query_gsi(self.organizers_table_name, "email-index", "email", email)
        return items[0] if items else None

    def get_organizer_by_verification_token(self, token: str) -> Optional[Dict[str, Any]]:
        items = self._query_gsi(self.organizers_table_name, "verification_token-index", "verification_token", token)
        return items[0] if items else None

    def get_organizer_by_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        items = self._query_gsi(self.organizers_table_name, "reset_token-index", "reset_token", token)
        return items[0] if items else None

    def update_organizer(self, organizer_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.organizers_table_name)
        expr, names, values = self._build_update_expression(update_data)
        response = table.update_item(
            Key={"OrganizerID": organizer_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW"
        )
        item = response.get("Attributes")
        return self._convert_decimals(item) if item else None

    def list_organizers(self) -> List[Dict[str, Any]]:
        return self._scan_all(self.organizers_table_name)

    # ── Events Table API ──────────────────────────────────────────────────────

    def create_event(self, event_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.events_table_name)
        item = {"EventID": event_id, **self._convert_floats(event_data), "created_at": _now_iso()}
        table.put_item(Item=item)
        return self._convert_decimals(item)

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.events_table_name)
        response = table.get_item(Key={"EventID": event_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def update_event(self, event_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.events_table_name)
        expr, names, values = self._build_update_expression(update_data)
        response = table.update_item(
            Key={"EventID": event_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW"
        )
        item = response.get("Attributes")
        return self._convert_decimals(item) if item else None

    def delete_event(self, event_id: str) -> None:
        table = self._get_table(self.events_table_name)
        table.delete_item(Key={"EventID": event_id})

    def list_events(self) -> List[Dict[str, Any]]:
        return self._scan_all(self.events_table_name)

    def list_events_by_status(self, status: str) -> List[Dict[str, Any]]:
        return self._query_gsi(self.events_table_name, "status-index", "status", status)

    def list_events_by_organizer(self, organizer_id: str) -> List[Dict[str, Any]]:
        return self._query_gsi(self.events_table_name, "organizer_id-index", "organizer_id", organizer_id)

    # ── Orders Table API ──────────────────────────────────────────────────────

    def create_order(self, order_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.orders_table_name)
        item = {"OrderID": order_id, **self._convert_floats(data), "created_at": _now_iso()}
        table.put_item(Item=item)
        return self._convert_decimals(item)

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.orders_table_name)
        response = table.get_item(Key={"OrderID": order_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def update_order(self, order_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.orders_table_name)
        expr, names, values = self._build_update_expression(update_data)
        response = table.update_item(
            Key={"OrderID": order_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW"
        )
        item = response.get("Attributes")
        return self._convert_decimals(item) if item else None

    def list_orders(self) -> List[Dict[str, Any]]:
        return self._scan_all(self.orders_table_name)

    def list_orders_by_event(self, event_id: str) -> List[Dict[str, Any]]:
        return self._query_gsi(self.orders_table_name, "event_id-index", "event_id", event_id)

    def list_orders_by_email(self, email: str) -> List[Dict[str, Any]]:
        return self._query_gsi(self.orders_table_name, "guest_email-index", "guest_email", email)

    # ── Tickets Table API ─────────────────────────────────────────────────────

    def create_ticket(self, ticket_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.tickets_table_name)
        item = {"TicketID": ticket_id, **self._convert_floats(data), "created_at": _now_iso()}
        table.put_item(Item=item)
        return self._convert_decimals(item)

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.tickets_table_name)
        response = table.get_item(Key={"TicketID": ticket_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def get_ticket_by_code(self, ticket_code: str) -> Optional[Dict[str, Any]]:
        if not ticket_code:
            return None
        code_clean = ticket_code.strip()
        items = self._query_gsi(self.tickets_table_name, "ticket_code-index", "ticket_code", code_clean)
        if not items and code_clean != code_clean.upper():
            items = self._query_gsi(self.tickets_table_name, "ticket_code-index", "ticket_code", code_clean.upper())
        if not items:
            item = self.get_ticket(code_clean)
            if item:
                return item
        return items[0] if items else None

    def list_tickets_by_order(self, order_id: str) -> List[Dict[str, Any]]:
        return self._query_gsi(self.tickets_table_name, "order_id-index", "order_id", order_id)

    def list_tickets_by_email(self, email: str) -> List[Dict[str, Any]]:
        return self._query_gsi(self.tickets_table_name, "attendee_email-index", "attendee_email", email)

    def update_ticket(self, ticket_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.tickets_table_name)
        expr, names, values = self._build_update_expression(update_data)
        response = table.update_item(
            Key={"TicketID": ticket_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW"
        )
        item = response.get("Attributes")
        return self._convert_decimals(item) if item else None

    # ── Promo Codes Table API ─────────────────────────────────────────────────

    def create_promo_code(self, code: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.promo_codes_table_name)
        item = {"Code": code, **self._convert_floats(data), "created_at": _now_iso()}
        table.put_item(Item=item)
        return self._convert_decimals(item)

    def get_promo_code(self, code: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.promo_codes_table_name)
        response = table.get_item(Key={"Code": code})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def list_promo_codes_by_event(self, event_id: str) -> List[Dict[str, Any]]:
        return self._query_gsi(self.promo_codes_table_name, "event_id-index", "event_id", event_id)

    def update_promo_code(self, code: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.promo_codes_table_name)
        expr, names, values = self._build_update_expression(update_data)
        response = table.update_item(
            Key={"Code": code},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW"
        )
        item = response.get("Attributes")
        return self._convert_decimals(item) if item else None


    def atomic_increment_promo_used_count(self, code: str, max_uses=None):
        """
        Atomically increment used_count. Conditionally capped by max_uses.
        Returns True on success, False if cap reached (ConditionalCheckFailedException).
        """
        from boto3.dynamodb.conditions import Attr
        table = self._get_table(self.promo_codes_table_name)
        kwargs = {
            "Key": {"Code": code},
            "UpdateExpression": "ADD used_count :one SET updated_at = :ts",
            "ExpressionAttributeValues": {":one": Decimal("1"), ":ts": _now_iso()},
            "ReturnValues": "NONE",
        }
        if max_uses is not None:
            kwargs["ConditionExpression"] = Attr("used_count").lt(int(max_uses))
        try:
            table.update_item(**kwargs)
            return True
        except table.meta.client.exceptions.ConditionalCheckFailedException:
            return False

    def atomic_reserve_ticket_inventory(
        self,
        event_id: str,
        ticket_type_id: str,
        quantity: int,
    ) -> bool:
        """
        Atomically increment quantity_sold for a specific ticket type inside the
        event's ticket_types list, using a read-modify-conditional-write loop.

        The event item stores ticket_types as a List attribute. DynamoDB does not
        support atomic updates to list elements by value, so we use an optimistic
        locking pattern:

          1. Read the current event item.
          2. Find the target ticket_type by id and verify remaining stock.
          3. Write the updated ticket_types list back with a ConditionExpression
             that checks quantity_sold is still at the value we read.
          4. If the condition fails (another writer updated it concurrently),
             retry up to MAX_RETRIES times before giving up.

        Returns True if the reservation succeeded, False if stock is exhausted
        or if optimistic locking retries are exceeded.
        """
        from botocore.exceptions import ClientError

        MAX_RETRIES = 5
        table = self._get_table(self.events_table_name)

        for attempt in range(MAX_RETRIES):
            # 1. Read current state
            response = table.get_item(Key={"EventID": event_id})
            event = response.get("Item")
            if not event:
                return False

            ticket_types = event.get("ticket_types", [])

            # 2. Locate target ticket_type and validate stock
            target_idx = None
            old_sold = None
            for idx, tt in enumerate(ticket_types):
                if str(tt.get("id", "")) == str(ticket_type_id):
                    target_idx = idx
                    old_sold = int(tt.get("quantity_sold", 0))
                    available = int(tt.get("quantity", 0)) - old_sold
                    if available < quantity:
                        return False  # Out of stock
                    break

            if target_idx is None:
                return False  # Ticket type not found

            # 3. Build updated list with incremented quantity_sold
            new_ticket_types = [dict(tt) for tt in ticket_types]
            new_ticket_types[target_idx]["quantity_sold"] = old_sold + quantity

            # 4. Conditional write: only succeeds if quantity_sold still equals
            # the value we read (optimistic lock). Uses raw client for list update.
            try:
                update_expr = "SET ticket_types = :new_tts, updated_at = :ts"
                expr_values = {
                    ":new_tts": self._convert_floats(new_ticket_types),
                    ":ts": _now_iso(),
                    ":expected_sold": Decimal(str(old_sold)),
                }
                # Condition: the specific list element's quantity_sold hasn't changed
                condition_expr = f"ticket_types[{target_idx}].quantity_sold = :expected_sold"
                table.update_item(
                    Key={"EventID": event_id},
                    UpdateExpression=update_expr,
                    ConditionExpression=condition_expr,
                    ExpressionAttributeValues=expr_values,
                )
                return True  # Reservation committed
            except ClientError as e:
                if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                    # Another request updated concurrently – retry
                    continue
                raise

        return False  # All retries exhausted

    # ── Resale Listings Table API ─────────────────────────────────────────────

    def create_resale_listing(self, listing_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.resale_listings_table_name)
        item = {"ListingID": listing_id, **self._convert_floats(data), "created_at": _now_iso()}
        table.put_item(Item=item)
        return self._convert_decimals(item)

    def get_resale_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.resale_listings_table_name)
        response = table.get_item(Key={"ListingID": listing_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def list_resale_listings_by_status(self, status: str) -> List[Dict[str, Any]]:
        return self._query_gsi(self.resale_listings_table_name, "status-index", "status", status)

    def list_resale_listings_by_ticket(self, ticket_id: str) -> List[Dict[str, Any]]:
        return self._query_gsi(self.resale_listings_table_name, "ticket_id-index", "ticket_id", ticket_id)

    def update_resale_listing(self, listing_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.resale_listings_table_name)
        expr, names, values = self._build_update_expression(update_data)
        response = table.update_item(
            Key={"ListingID": listing_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW"
        )
        item = response.get("Attributes")
        return self._convert_decimals(item) if item else None

    # ── Transfers Table API ───────────────────────────────────────────────────

    def create_transfer(self, transfer_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.transfers_table_name)
        item = {"TransferID": transfer_id, **self._convert_floats(data), "created_at": _now_iso()}
        table.put_item(Item=item)
        return self._convert_decimals(item)

    def get_transfer(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.transfers_table_name)
        response = table.get_item(Key={"TransferID": transfer_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def list_transfers_by_ticket(self, ticket_id: str) -> List[Dict[str, Any]]:
        return self._query_gsi(self.transfers_table_name, "ticket_id-index", "ticket_id", ticket_id)

    # ── Payouts Table API ─────────────────────────────────────────────────────

    def create_payout(self, payout_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.payouts_table_name)
        item = {"PayoutID": payout_id, **self._convert_floats(data), "created_at": _now_iso()}
        table.put_item(Item=item)
        return self._convert_decimals(item)

    def get_payout(self, payout_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.payouts_table_name)
        response = table.get_item(Key={"PayoutID": payout_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def update_payout(self, payout_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.payouts_table_name)
        expr, names, values = self._build_update_expression(update_data)
        response = table.update_item(
            Key={"PayoutID": payout_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW"
        )
        item = response.get("Attributes")
        return self._convert_decimals(item) if item else None

    def list_payouts_by_organizer(self, organizer_id: str) -> List[Dict[str, Any]]:
        return self._query_gsi(self.payouts_table_name, "organizer_id-index", "organizer_id", organizer_id)

    def list_payouts(self) -> List[Dict[str, Any]]:
        return self._scan_all(self.payouts_table_name)

    # ── Platform Settings Table API ───────────────────────────────────────────

    def set_platform_setting(self, key: str, value: Any) -> Dict[str, Any]:
        table = self._get_table(self.platform_settings_table_name)
        item = {"SettingKey": key, "value": value, "updated_at": _now_iso()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_platform_setting(self, key: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.platform_settings_table_name)
        response = table.get_item(Key={"SettingKey": key})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def list_platform_settings(self) -> List[Dict[str, Any]]:
        return self._scan_all(self.platform_settings_table_name)

    # ── Audit Logs Table API ──────────────────────────────────────────────────

    def create_audit_log(self, data: Dict[str, Any]) -> Dict[str, Any]:
        log_id = _new_id()
        table = self._get_table(self.audit_logs_table_name)
        item = {"LogID": log_id, **self._convert_floats(data), "timestamp": _now_iso()}
        table.put_item(Item=item)
        return self._convert_decimals(item)

    def list_audit_logs(self) -> List[Dict[str, Any]]:
        return self._scan_all(self.audit_logs_table_name)

    # ── Event Categories Table API ────────────────────────────────────────────

    def create_category(self, category_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.event_categories_table_name)
        item = {"CategoryID": category_id, **self._convert_floats(data)}
        table.put_item(Item=item)
        return self._convert_decimals(item)

    def get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.event_categories_table_name)
        response = table.get_item(Key={"CategoryID": category_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def get_category_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        items = self._scan_all(self.event_categories_table_name)
        for item in items:
            if item.get("slug") == slug or item.get("CategoryID") == slug:
                return item
        return None

    def list_categories(self) -> List[Dict[str, Any]]:
        cats = self._scan_all(self.event_categories_table_name)
        if not cats:
            default_cats = [
                {"CategoryID": "cat-1", "name": "Music & Concerts", "description": "Live shows, festivals & tours", "slug": "music-concerts", "sort_order": 1},
                {"CategoryID": "cat-2", "name": "Tech & Cloud Summits", "description": "Developer conferences, AI & AWS summits", "slug": "tech-cloud-summits", "sort_order": 2},
                {"CategoryID": "cat-3", "name": "Business & Startup", "description": "Networking, pitch days & workshops", "slug": "business-startup", "sort_order": 3},
                {"CategoryID": "cat-4", "name": "Arts & Theatre", "description": "Plays, comedy & exhibitions", "slug": "arts-theatre", "sort_order": 4},
                {"CategoryID": "cat-5", "name": "Sports & Gaming", "description": "Tournaments, esports & matches", "slug": "sports-gaming", "sort_order": 5},
                {"CategoryID": "cat-6", "name": "Workshops & Masterclasses", "description": "Skill building & hands-on bootcamps", "slug": "workshops-masterclasses", "sort_order": 6}
            ]
            for c in default_cats:
                self.create_category(c)
            return default_cats
        return cats

    def delete_category(self, category_id: str) -> None:
        table = self._get_table(self.event_categories_table_name)
        table.delete_item(Key={"CategoryID": category_id})

    # ── Health check ──────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Verify DynamoDB connectivity by describing the events table."""
        try:
            client = boto3.client("dynamodb", region_name=self.region)
            client.describe_table(TableName=self.events_table_name)
            return True
        except Exception:
            return False


# Singleton instance
dynamodb_helper = DynamoDBHelper()
