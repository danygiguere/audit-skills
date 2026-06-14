# Deliberately vulnerable sample — the file audited in the demo.
# Six bugs a pattern-based scanner (SonarQube, Semgrep, CodeQL) can't find,
# because each needs reasoning about ownership, concurrency, retries, or money:
#   1. IDOR / authorization — withdraws from any account id, no ownership check
#   2. Race condition       — balance checked, then deducted in a separate step
#   3. Atomicity            — local debit + external payout, no transaction
#   4. Idempotency          — no idempotency key; a retry pays out twice
#   5. Negative-amount abuse — amount unvalidated; a negative value mints money
#   6. Wrong balance on reject — the response is computed outside the check, so
#                                a declined withdrawal still reports a deduction
#
# Run `/audit demo/vulnerable_sample.py` and the audit should flag all six.
# This file is a fixture, not real code.

from flask import Flask, request, jsonify, session
from db import db                # db.accounts.get(id) / .update(id, **fields)
from payments import gateway     # gateway.payout(iban, amount) — external call

app = Flask(__name__)


@app.post("/accounts/<int:account_id>/withdraw")
def withdraw(account_id):
    amount = request.get_json()["amount"]

    # IDOR: the account is fetched by the path id alone — the caller is never
    # checked as its owner (session["user_id"]), so anyone can drain anyone.
    account = db.accounts.get(account_id)

    # Race condition: the balance is checked here and deducted two lines down
    # in a separate statement. Two concurrent withdrawals both pass the check
    # and both deduct — the account overdraws. No lock, no atomic update.
    if account.balance >= amount:
        # Atomicity: the local debit and the external payout are not one unit.
        # If the payout fails or the process dies between them, the ledger and
        # the money disagree — with no compensation.
        db.accounts.update(account_id, balance=account.balance - amount)
        # Idempotency: no idempotency key. A client double-click or a network
        # retry re-runs this handler and pays out a second time.
        gateway.payout(account.iban, amount)

    return jsonify({"balance": account.balance - amount})
