from typing import List, Dict, Any, Tuple
from simunation.agent import Agent
from simunation.config import config

class Economy:
    def __init__(self):
        self.bids: List[Dict[str, Any]] = []
        self.asks: List[Dict[str, Any]] = []
        self.transaction_history: List[Dict[str, Any]] = []
        self.current_average_price: float = config.base_food_price

    def submit_orders(self, orders: List[Dict[str, Any]]):
        """Submit buy and sell orders into the market pools."""
        for order in orders:
            if order["type"] == "buy":
                self.bids.append(order)
            elif order["type"] == "sell":
                self.asks.append(order)

    def match_orders(self, agents_dict: Dict[int, Agent]) -> List[Dict[str, Any]]:
        """
        Executes a double-auction matching process:
        - Sort bids descending (buyers willing to pay the most matched first).
        - Sort asks ascending (sellers willing to accept the least matched first).
        - Match when bid_price >= ask_price.
        - Transaction price is the average of bid and ask.
        """
        # Sort bids descending, asks ascending
        self.bids.sort(key=lambda x: x["price"], reverse=True)
        self.asks.sort(key=lambda x: x["price"])

        matched_trades = []
        bid_idx = 0
        ask_idx = 0

        while bid_idx < len(self.bids) and ask_idx < len(self.asks):
            bid = self.bids[bid_idx]
            ask = self.asks[ask_idx]

            # Check if buyer and seller are the same agent
            if bid["agent_id"] == ask["agent_id"]:
                # Bypass self-matching
                if len(self.bids) - bid_idx > len(self.asks) - ask_idx:
                    bid_idx += 1
                else:
                    ask_idx += 1
                continue

            # Check if trade is possible
            if bid["price"] >= ask["price"]:
                buyer = agents_dict[bid["agent_id"]]
                seller = agents_dict[ask["agent_id"]]

                # Determine volume and price
                trade_volume = min(bid["amount"], ask["amount"])
                trade_price = round((bid["price"] + ask["price"]) / 2.0, 2)
                total_cost = round(trade_volume * trade_price, 2)

                # Ensure buyer has enough money
                if buyer.money < total_cost:
                    # Scale down trade volume to what buyer can afford
                    if buyer.money > 0.05:
                        trade_volume = buyer.money / trade_price
                        total_cost = round(trade_volume * trade_price, 2)
                    else:
                        trade_volume = 0.0

                # Ensure seller has enough food
                if seller.food < trade_volume:
                    trade_volume = seller.food
                    total_cost = round(trade_volume * trade_price, 2)

                if trade_volume > 0.01:
                    # Execute exchange
                    buyer.money -= total_cost
                    buyer.food += trade_volume
                    seller.money += total_cost
                    seller.food -= trade_volume

                    # Record transaction
                    trade_info = {
                        "buyer_id": buyer.id,
                        "buyer_role": buyer.role,
                        "seller_id": seller.id,
                        "seller_role": seller.role,
                        "amount": round(trade_volume, 2),
                        "price": trade_price,
                        "total": total_cost
                    }
                    matched_trades.append(trade_info)
                    self.transaction_history.append(trade_info)

                    # Update agent memories
                    buyer.record_trade("buyer", trade_volume, trade_price, True)
                    seller.record_trade("seller", trade_volume, trade_price, True)

                    # Update remaining quantities
                    bid["amount"] -= trade_volume
                    ask["amount"] -= trade_volume

                # Advance pointer or remove filled orders
                if bid["amount"] <= 0.01:
                    bid_idx += 1
                if ask["amount"] <= 0.01:
                    ask_idx += 1
            else:
                # Highest bid is less than lowest ask; no more matches possible
                break

        # Record failed trades in remaining agents' memories to help them adapt pricing
        for i in range(bid_idx, len(self.bids)):
            buyer = agents_dict[self.bids[i]["agent_id"]]
            buyer.record_trade("buyer", self.bids[i]["amount"], self.bids[i]["price"], False)

        for i in range(ask_idx, len(self.asks)):
            seller = agents_dict[self.asks[i]["agent_id"]]
            seller.record_trade("seller", self.asks[i]["amount"], self.asks[i]["price"], False)

        # Clear order book for next step
        self.bids = []
        self.asks = []

        # Calculate average market price for this step
        if matched_trades:
            total_value = sum(t["amount"] * t["price"] for t in matched_trades)
            total_amount = sum(t["amount"] for t in matched_trades)
            self.current_average_price = round(total_value / total_amount, 2)
        
        # Keep transaction history capped
        if len(self.transaction_history) > 100:
            self.transaction_history = self.transaction_history[-100:]

        return matched_trades
