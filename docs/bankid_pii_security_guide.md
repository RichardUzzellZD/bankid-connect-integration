# BankID PII Security Guide - Quick Reference

## 🔒 Golden Rule
**NO PII BEFORE AUTHENTICATION ✅**

---

## Flow Comparison

### ❌ WRONG WAY (Exposes PII)

```
Customer calls → "I have you on record as Mona Munster, born 1985"
                                    ↓
                            Press 1 to confirm
                                    ↓
                            BankID authentication
```

**Problems:**
- Anyone with customer's phone hears their name and DOB
- Fails GDPR "minimum necessary" principle
- Fraud risk if wrong person has the phone
- PII disclosed before identity proven

---

### ✅ RIGHT WAY (PII-Safe)

```
Customer calls → "For security, check your BankID app"
                                    ↓
                            BankID authentication
                                    ↓
                    "Thank you, Mona. You're verified."
```

**Benefits:**
- Zero PII disclosure before auth
- GDPR compliant
- Fraud prevention
- Better security posture

---

## Voice Prompts

### ❌ BEFORE Authentication (Generic Only)

```
✅ "Welcome. For security, we need to verify your identity."

✅ "I'm sending an authentication request to your BankID app. 
    Please check your mobile phone."

✅ "Waiting for authentication to complete..."

✅ [Hold music / Silence]
```

### ✅ AFTER Authentication (Personalized OK)

```
✅ "Thank you, Mona. Your identity has been verified."

✅ "Hello Mona, how can we help you today?"

✅ "I can see your account information. Let me check that for you."
```

### ❌ AFTER Failed Authentication (Generic Again)

```
✅ "Unable to verify your identity at this time. 
    I'm connecting you to an agent who can help."

❌ "Unable to verify Mona Munster. Connecting you to an agent."
    (Don't use name if auth failed!)
```

---

## Summary

| Scenario | Voice Prompt | PII Disclosed? |
|----------|--------------|----------------|
| **Before Auth** | "Check your BankID app" | ❌ No |
| **During Auth** | [Hold music] | ❌ No |
| **After Success** | "Thank you, Mona" | ✅ Yes |
| **After Failure** | "Unable to verify" | ❌ No |
| **Unknown Caller** | "No information on file" | ❌ No |
| **Transfer to Agent** | "Connecting you..." | ❌ No (screen only) |

---

## Key Takeaways

1. 🔒 **Lookup silently** - fetchCustomerData runs without speaking
2. 🔒 **Store, don't speak** - Contact attributes stored, not voiced
3. 🔒 **Authenticate first** - BankID before any PII disclosure
4. 🔒 **Generic prompts** - "Check your phone" not "Hi, Mona"
5. 🔒 **Personalize after** - Only use name after verification
6. 🔒 **Fail safely** - Errors never expose PII

**When in doubt: Don't say it out loud until BankID says it's OK!** ✅
