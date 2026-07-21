import os
import boto3
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.core.config import settings

class DynamoDBHelper:
    def __init__(self):
        self.region = settings.AWS_REGION
        self.environment = os.environ.get("ENV", "dev")
        
        # Load table names from environment or use default naming conventions mapped to Terraform
        self.events_table_name = os.environ.get("EVENTS_TABLE", f"alphapass-events-{self.environment}")
        self.registrations_table_name = os.environ.get("REGISTRATIONS_TABLE", f"alphapass-registrations-{self.environment}")
        self.organizers_table_name = os.environ.get("ORGANIZERS_TABLE", f"alphapass-organizers-{self.environment}")
        self.admins_table_name = os.environ.get("ADMINS_TABLE", f"alphapass-admins-{self.environment}")
        self.orders_table_name = os.environ.get("ORDERS_TABLE", f"alphapass-orders-{self.environment}")
        self.tickets_table_name = os.environ.get("TICKETS_TABLE", f"alphapass-tickets-{self.environment}")
        self.promo_codes_table_name = os.environ.get("PROMO_CODES_TABLE", f"alphapass-promo-codes-{self.environment}")
        self.resale_listings_table_name = os.environ.get("RESALE_LISTINGS_TABLE", f"alphapass-resale-listings-{self.environment}")
        self.transfers_table_name = os.environ.get("TRANSFERS_TABLE", f"alphapass-transfers-{self.environment}")
        self.payouts_table_name = os.environ.get("PAYOUTS_TABLE", f"alphapass-payouts-{self.environment}")
        self.platform_settings_table_name = os.environ.get("PLATFORM_SETTINGS_TABLE", f"alphapass-platform-settings-{self.environment}")
        self.audit_logs_table_name = os.environ.get("AUDIT_LOGS_TABLE", f"alphapass-audit-logs-{self.environment}")
        self.event_categories_table_name = os.environ.get("EVENT_CATEGORIES_TABLE", f"alphapass-event-categories-{self.environment}")
        
        self.resource = boto3.resource("dynamodb", region_name=self.region)

    # Generic Table accessors
    def _get_table(self, table_name: str):
        return self.resource.Table(table_name)

    def _convert_floats(self, item: Any) -> Any:
        """Recursively convert float values to Decimal, required by DynamoDB."""
        if isinstance(item, list):
            return [self._convert_floats(x) for x in item]
        elif isinstance(item, dict):
            return {k: self._convert_floats(v) for k, v in item.items()}
        elif isinstance(item, float):
            return Decimal(str(item))
        return item

    def _convert_decimals(self, item: Any) -> Any:
        """Recursively convert Decimal values back to python standard formats."""
        if isinstance(item, list):
            return [self._convert_decimals(x) for x in item]
        elif isinstance(item, dict):
            return {k: self._convert_decimals(v) for k, v in item.items()}
        elif isinstance(item, Decimal):
            if item % 1 == 0:
                return int(item)
            return float(item)
        return item

    # ── Organizers Table API ──────────────────────────────────────────────────
    def create_organizer(self, organizer_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.organizers_table_name)
        item = {"OrganizerID": organizer_id, **data, "created_at": datetime.now(timezone.utc).isoformat()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_organizer(self, organizer_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.organizers_table_name)
        response = table.get_item(Key={"OrganizerID": organizer_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    # ── Admins Table API ──────────────────────────────────────────────────────
    def create_admin(self, admin_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.admins_table_name)
        item = {"AdminID": admin_id, **data, "created_at": datetime.now(timezone.utc).isoformat()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_admin(self, admin_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.admins_table_name)
        response = table.get_item(Key={"AdminID": admin_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    # ── Events Table API ──────────────────────────────────────────────────────
    def create_event(self, event_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.events_table_name)
        item = {"EventID": event_id, **event_data, "created_at": datetime.now(timezone.utc).isoformat()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.events_table_name)
        response = table.get_item(Key={"EventID": event_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def list_events(self) -> List[Dict[str, Any]]:
        table = self._get_table(self.events_table_name)
        response = table.scan()
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return self._convert_decimals(items)

    def update_event(self, event_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.events_table_name)
        update_data = self._convert_floats(update_data)
        
        update_expression = "SET "
        expression_attribute_names = {}
        expression_attribute_values = {}
        
        for idx, (k, v) in enumerate(update_data.items()):
            attr_name = f"#attr_{k}"
            val_name = f":val_{k}"
            update_expression += f"{attr_name} = {val_name}, "
            expression_attribute_names[attr_name] = k
            expression_attribute_values[val_name] = v
            
        update_expression += "#attr_updated_at = :val_updated_at"
        expression_attribute_names["#attr_updated_at"] = "updated_at"
        expression_attribute_values[":val_updated_at"] = datetime.now(timezone.utc).isoformat()
        
        response = table.update_item(
            Key={"EventID": event_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW"
        )
        item = response.get("Attributes")
        return self._convert_decimals(item) if item else None

    # ── Orders Table API ──────────────────────────────────────────────────────
    def create_order(self, order_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.orders_table_name)
        item = {"OrderID": order_id, **data, "created_at": datetime.now(timezone.utc).isoformat()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.orders_table_name)
        response = table.get_item(Key={"OrderID": order_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    # ── Tickets Table API ─────────────────────────────────────────────────────
    def create_ticket(self, ticket_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.tickets_table_name)
        item = {"TicketID": ticket_id, **data, "created_at": datetime.now(timezone.utc).isoformat()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.tickets_table_name)
        response = table.get_item(Key={"TicketID": ticket_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def update_ticket(self, ticket_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.tickets_table_name)
        update_data = self._convert_floats(update_data)
        
        update_expression = "SET "
        expression_attribute_names = {}
        expression_attribute_values = {}
        
        for k, v in update_data.items():
            attr_name = f"#attr_{k}"
            val_name = f":val_{k}"
            update_expression += f"{attr_name} = {val_name}, "
            expression_attribute_names[attr_name] = k
            expression_attribute_values[val_name] = v
            
        update_expression = update_expression.rstrip(", ")
        
        response = table.update_item(
            Key={"TicketID": ticket_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW"
        )
        item = response.get("Attributes")
        return self._convert_decimals(item) if item else None

    # ── Promo Codes Table API ─────────────────────────────────────────────────
    def create_promo_code(self, code: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.promo_codes_table_name)
        item = {"Code": code, **data, "created_at": datetime.now(timezone.utc).isoformat()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_promo_code(self, code: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.promo_codes_table_name)
        response = table.get_item(Key={"Code": code})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    # ── Resale Listings Table API ─────────────────────────────────────────────
    def create_resale_listing(self, listing_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.resale_listings_table_name)
        item = {"ListingID": listing_id, **data, "created_at": datetime.now(timezone.utc).isoformat()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_resale_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.resale_listings_table_name)
        response = table.get_item(Key={"ListingID": listing_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def list_resale_listings(self) -> List[Dict[str, Any]]:
        table = self._get_table(self.resale_listings_table_name)
        response = table.scan()
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return self._convert_decimals(items)

    # ── Ticket Transfers Table API ────────────────────────────────────────────
    def create_transfer(self, transfer_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.transfers_table_name)
        item = {"TransferID": transfer_id, **data, "created_at": datetime.now(timezone.utc).isoformat()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_transfer(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.transfers_table_name)
        response = table.get_item(Key={"TransferID": transfer_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    # ── Organizer Payouts Table API ───────────────────────────────────────────
    def create_payout(self, payout_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.payouts_table_name)
        item = {"PayoutID": payout_id, **data, "created_at": datetime.now(timezone.utc).isoformat()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_payout(self, payout_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.payouts_table_name)
        response = table.get_item(Key={"PayoutID": payout_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    # ── Platform Settings Table API ───────────────────────────────────────────
    def set_platform_setting(self, key: str, value: Any) -> Dict[str, Any]:
        table = self._get_table(self.platform_settings_table_name)
        item = {"SettingKey": key, "value": value, "updated_at": datetime.now(timezone.utc).isoformat()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_platform_setting(self, key: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.platform_settings_table_name)
        response = table.get_item(Key={"SettingKey": key})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    # ── Audit Logs Table API ──────────────────────────────────────────────────
    def create_audit_log(self, log_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.audit_logs_table_name)
        item = {"LogID": log_id, **data, "timestamp": datetime.now(timezone.utc).isoformat()}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def list_audit_logs(self) -> List[Dict[str, Any]]:
        table = self._get_table(self.audit_logs_table_name)
        response = table.scan()
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return self._convert_decimals(items)

    # ── Event Categories Table API ────────────────────────────────────────────
    def create_category(self, category_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(self.event_categories_table_name)
        item = {"CategoryID": category_id, **data}
        table.put_item(Item=self._convert_floats(item))
        return self._convert_decimals(item)

    def get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        table = self._get_table(self.event_categories_table_name)
        response = table.get_item(Key={"CategoryID": category_id})
        item = response.get("Item")
        return self._convert_decimals(item) if item else None

    def list_categories(self) -> List[Dict[str, Any]]:
        table = self._get_table(self.event_categories_table_name)
        response = table.scan()
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return self._convert_decimals(items)

# Singleton instance
dynamodb_helper = DynamoDBHelper()
