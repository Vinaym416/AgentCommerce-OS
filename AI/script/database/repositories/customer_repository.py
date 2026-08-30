"""
AGENTCOMMERCE OS
Customer Repository

Responsible for customer persistence and retrieval.
"""

from typing import Optional, Dict, Any

from script.database.mongodb import get_database


class CustomerRepository:

    def __init__(self):

        self.db = get_database()

        self.collection = self.db["customers"]


    # ========================================================
    # GET CUSTOMER
    # ========================================================

    def get_by_customer_id(
        self,
        customer_id: int
    ) -> Optional[Dict[str, Any]]:

        return self.collection.find_one(
            {
                "customer_id": customer_id
            },
            {
                "_id": 0
            }
        )


    # ========================================================
    # CREATE CUSTOMER
    # ========================================================

    def create(
        self,
        customer: Dict[str, Any]
    ):

        result = self.collection.insert_one(
            customer
        )

        return result.inserted_id


    # ========================================================
    # UPSERT CUSTOMER
    # ========================================================

    def upsert(
        self,
        customer: Dict[str, Any]
    ):

        customer_id = customer["customer_id"]

        return self.collection.update_one(

            {
                "customer_id": customer_id
            },

            {
                "$set": customer
            },

            upsert=True
        )


    # ========================================================
    # COUNT CUSTOMERS
    # ========================================================

    def count(self) -> int:

        return self.collection.count_documents({})