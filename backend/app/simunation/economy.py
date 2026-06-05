from typing import List, Dict, Any, Tuple
from simunation.config import config

class MarketOrder:
    def __init__(self, agent_id: int, order_type: str, item: str, amount: float, price: float):
        self.agent_id: int = agent_id
        self.type: str = order_type  # "buy" or "sell"
        self.item: str = item  # "food", "raw_materials", "housing", "medical_service", "education"
        self.amount: float = amount
        self.price: float = price

class AdvancedEconomy:
    def __init__(self):
        # Maps item name -> list of orders
        self.bids: Dict[str, List[MarketOrder]] = {
            "food": [], "raw_materials": [], "housing": [], "medical_service": [], "education": []
        }
        self.asks: Dict[str, List[MarketOrder]] = {
            "food": [], "raw_materials": [], "housing": [], "medical_service": [], "education": []
        }
        self.price_history: Dict[str, List[float]] = {
            k: [config.base_prices[k]] for k in config.base_prices
        }
        self.average_prices: Dict[str, float] = config.base_prices.copy()
        self.volume_history: Dict[str, List[float]] = {k: [] for k in config.base_prices}

    def get_avg_price(self, item: str) -> float:
        return self.average_prices.get(item, config.base_prices.get(item, 10.0))

    def submit_order(self, order: MarketOrder):
        if order.type == "buy":
            self.bids[order.item].append(order)
        else:
            self.asks[order.item].append(order)

    def match_item_market(self, item: str, agents_dict: Dict[int, Any], step: int) -> List[Dict[str, Any]]:
        bids_list = self.bids[item]
        asks_list = self.asks[item]

        bids_list.sort(key=lambda x: x.price, reverse=True)
        asks_list.sort(key=lambda x: x.price)

        trades = []
        bid_idx, ask_idx = 0, 0

        while bid_idx < len(bids_list) and ask_idx < len(asks_list):
            bid = bids_list[bid_idx]
            ask = asks_list[ask_idx]

            if bid.agent_id == ask.agent_id:
                # Bypass self-matching
                if len(bids_list) - bid_idx > len(asks_list) - ask_idx:
                    bid_idx += 1
                else:
                    ask_idx += 1
                continue

            if bid.price >= ask.price:
                buyer = agents_dict[bid.agent_id]
                seller = agents_dict[ask.agent_id]

                trade_volume = min(bid.amount, ask.amount)
                trade_price = round((bid.price + ask.price) / 2.0, 2)
                total_cost = round(trade_volume * trade_price, 2)

                # Buyer budget checks
                if buyer.money < total_cost:
                    if buyer.money > 0.05:
                        trade_volume = buyer.money / trade_price
                        total_cost = round(trade_volume * trade_price, 2)
                    else:
                        trade_volume = 0.0

                # Seller inventory checks
                seller_stock = seller.get_item_stock(item)
                if seller_stock < trade_volume:
                    trade_volume = seller_stock
                    total_cost = round(trade_volume * trade_price, 2)

                if trade_volume > 0.01:
                    # Adjust balances
                    buyer.money -= total_cost
                    seller.money += total_cost
                    
                    # Update inventory
                    buyer.add_item_stock(item, trade_volume)
                    seller.sub_item_stock(item, trade_volume)

                    # Trigger service consumption effect
                    buyer.consume_purchased_item(item, trade_volume)

                    # Log trade
                    trade_info = {
                        "buyer_id": buyer.id,
                        "buyer_role": buyer.role,
                        "seller_id": seller.id,
                        "seller_role": seller.role,
                        "item": item,
                        "amount": round(trade_volume, 2),
                        "price": trade_price,
                        "total": total_cost
                    }
                    trades.append(trade_info)

                    # Modify Relationship Trust: successful trade builds trust
                    buyer.relationships.modify_trust(seller.id, 5.0, f"Bought {item} from {seller.id}", step)
                    seller.relationships.modify_trust(buyer.id, 5.0, f"Sold {item} to {buyer.id}", step)

                    bid.amount -= trade_volume
                    ask.amount -= trade_volume

                if bid.amount <= 0.01:
                    bid_idx += 1
                if ask.amount <= 0.01:
                    ask_idx += 1
            else:
                break

        # Record failures to update price perception
        for i in range(bid_idx, len(bids_list)):
            agents_dict[bids_list[i].agent_id].relationships.modify_trust(
                bids_list[i].agent_id, 0.0, f"Failed buy order for {item}", step
            )
        for i in range(ask_idx, len(asks_list)):
            agents_dict[asks_list[i].agent_id].relationships.modify_trust(
                asks_list[i].agent_id, 0.0, f"Failed sell order for {item}", step
            )

        # Clear listings
        self.bids[item] = []
        self.asks[item] = []

        # Update average prices
        if trades:
            tot_val = sum(t["amount"] * t["price"] for t in trades)
            tot_amt = sum(t["amount"] for t in trades)
            avg = round(tot_val / tot_amt, 2)
            self.average_prices[item] = avg
            self.price_history[item].append(avg)
            self.volume_history[item].append(tot_amt)
        else:
            self.volume_history[item].append(0.0)
            # Drift price slightly if no trades happen
            if item == "food":
                self.average_prices[item] = max(config.base_prices[item] * 0.2, self.average_prices[item] * 0.98)

        # Limit history
        if len(self.price_history[item]) > 100:
            self.price_history[item].pop(0)
        if len(self.volume_history[item]) > 100:
            self.volume_history[item].pop(0)

        return trades
