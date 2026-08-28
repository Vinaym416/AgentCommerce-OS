"""Payment preparation boundary for approved commerce decisions."""

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4


@dataclass
class PaymentResult:
	status: str
	product_id: Optional[int]
	amount: float
	currency: str
	payment_method: str
	transaction_id: Optional[str]
	reason: str


class PaymentAgent:
	SUPPORTED_PAYMENT_METHODS = {"UPI", "CARD", "NET_BANKING", "WALLET"}

	def __init__(self):
		print("Payment Agent initialized.")

	def process_payment(
		self,
		product_id: int,
		amount: float,
		payment_method: str = "UPI",
		simulate_failure: bool = False,
	) -> PaymentResult:
		if amount <= 0:
			return PaymentResult(
				status="PAYMENT_FAILED",
				product_id=product_id,
				amount=amount,
				currency="INR",
				payment_method=payment_method,
				transaction_id=None,
				reason="invalid_amount",
			)

		normalized_method = payment_method.upper()

		if normalized_method not in self.SUPPORTED_PAYMENT_METHODS:
			return PaymentResult(
				status="PAYMENT_FAILED",
				product_id=product_id,
				amount=round(amount, 2),
				currency="INR",
				payment_method=payment_method,
				transaction_id=None,
				reason="unsupported_payment_method",
			)

		if simulate_failure:
			return PaymentResult(
				status="PAYMENT_FAILED",
				product_id=product_id,
				amount=round(amount, 2),
				currency="INR",
				payment_method=normalized_method,
				transaction_id=None,
				reason="payment_declined",
			)

		return PaymentResult(
			status="PAYMENT_SUCCESS",
			product_id=product_id,
			amount=round(amount, 2),
			currency="INR",
			payment_method=normalized_method,
			transaction_id=f"TXN-{uuid4().hex[:12].upper()}",
			reason="payment_processed_successfully",
		)


def main():
	agent = PaymentAgent()

	tests = [
		{"product_id": 453, "amount": 705.81, "payment_method": "UPI"},
		{"product_id": 453, "amount": 0, "payment_method": "UPI"},
		{"product_id": 453, "amount": 705.81, "payment_method": "CASH"},
		{
			"product_id": 453,
			"amount": 705.81,
			"payment_method": "UPI",
			"simulate_failure": True,
		},
		{"product_id": 453, "amount": 705.81, "payment_method": "UPI"},
	]

	for test in tests:
		print("\nTEST")
		print(test)
		print(agent.process_payment(**test))


if __name__ == "__main__":
	main()
