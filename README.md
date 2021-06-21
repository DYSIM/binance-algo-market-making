# Algorithmic Market Maker on Binance testnet.

Using [Binance's Api](https://binance-docs.github.io/apidocs/spot/en/#change-log), a market maker bot is implemented to provide bid ask algorithmically on the Binance testnet, which uses dummy currencies and trades. The library [binance-connector-python](https://github.com/binance/binance-connector-python/) is used to interface with Binance's API.


The implementation is encompassed in binanceMM.py and the market maker strategy is as follows:
1. Get the latest trade price
2. set up symmetric bid ask orders around the price given a spread and constant quantity
3. if an order is filled, cancel all remaining orders and set a new bid ask again

The strategy is very naive and as expected the average profit is negative for this. The point of this exercise, for me, is to explore Binance's API and implementation more so than the actual market making strategy. More sophisticated strategies can be explored in the future.


# Instructions

You require a BInance Exchange API key and Secret key in a readable file format within the directory.

```python
pip install -r requirements.txt
python binanceMM.py
```

