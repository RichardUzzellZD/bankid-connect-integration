# Finnish BankID Implementation - Amazon Connect Integration

## Overview
Authenticate customers during Amazon Connect calls using Finnish BankID with DynamoDB pre-population.

## Authentication Flow (PII-Safe)

**🔒 SECURITY PRINCIPLE: No PII spoken until AFTER authentication succeeds**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Customer Calls                                               │
│    └─→ Phone: +358401234567                                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Invoke fetchCustomerData Lambda (SILENT LOOKUP)             │
│    └─→ Lookup by phone in GenericDB                           │
│    └─→ Returns: firstName, lastName, DoB, personalNumber      │
│    └─→ Store in contact attributes (NOT spoken)               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Check if Customer Found                                      │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                     ┌──────┴──────┐
                     │             │
              Customer Found    Not Found
                     │             │
                     ↓             ↓
         ┌──────────────────┐   Transfer to Agent
         │ Continue BankID  │   (Manual Verification)
         └──────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Play Prompt (NO PII DISCLOSED)                              │
│    "For security, we need to verify your identity.             │
│     I'm sending an authentication request to your BankID app.  │
│     Please check your mobile phone."                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Invoke bankIDAuthenticateLambda                             │
│    Input: personalNumber from DynamoDB (silent)                │
│    Action: Initiate BankID authentication                      │
│    Return: orderRef (tracking ID)                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Poll BankID Status (Loop)                                    │
│    Invoke: bankIDStatusCheckLambda                             │
│    Input: orderRef                                              │
│    Check every 2 seconds for up to 30 seconds                 │
│    Play hold music/silence (NO prompts with PII)              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                     ┌──────┴──────┐
                     │             │
                 Complete      Timeout/Failed
                     │             │
                     ↓             ↓
         ┌──────────────────┐   ┌──────────────────┐
         │ 7. Authenticated │   │ 7b. Failed Auth  │
         └──────────────────┘   └──────────────────┘
                     │                      │
                     ↓                      ↓
┌─────────────────────────────────────┐   Transfer to Agent
│ 8. NOW SAFE TO USE PII              │   "Unable to verify.
│    Play Prompt:                     │    Connecting you to
│    "Thank you, {firstName}.         │    an agent."
│     Your identity has been verified.│
│     How can we help you today?"     │
└─────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ 9. Update Contact Attributes                                    │
│    bankid_verified = "true"                                     │
│    bankid_timestamp = "2026-07-02T14:30:00Z"                   │
│    verification_method = "bankid_mobile"                        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 10. Continue Normal Flow                                        │
│     → forethoughtPostLambda (includes verified status)         │
│     → Transfer to Forethought Bot                              │
│     → Transfer to Queue/Agent                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Lambda Functions Required

### 1. bankIDAuthenticateLambda

**Purpose:** Initiate BankID authentication request

**Input:**
```json
{
  "Details": {
    "Parameters": {
      "personalNumber": "198509221234",
      "endUserIp": "192.0.2.1"
    }
  }
}
```

**Output:**
```json
{
  "orderRef": "131daac9-16c6-4618-beb0-365768f37288",
  "autoStartToken": "7c40b5c9-fa74-49cf-b98c-bfe651f9a7c6",
  "status": "pending"
}
```

### 2. bankIDStatusCheckLambda

**Purpose:** Check authentication status (polling)

**Input:**
```json
{
  "Details": {
    "Parameters": {
      "orderRef": "131daac9-16c6-4618-beb0-365768f37288"
    }
  }
}
```

**Response Scenarios:**

**Complete:**
```json
{
  "status": "complete",
  "verified": "true",
  "givenName": "Mona",
  "surname": "Munster",
  "personalNumber": "198509221234"
}
```

**Pending:**
```json
{
  "status": "pending",
  "hintCode": "outstandingTransaction"
}
```

**Failed:**
```json
{
  "status": "failed",
  "hintCode": "userCancel"
}
```

## Test Environment Setup

### 1. Get Test BankID

**Option A: Swedish Test Environment (Recommended)**
```
1. Go to: https://demo.bankid.com
2. Click "Order test BankID"
3. Fill in test personal number request form
4. Download test BankID security app
5. Install test BankID using provided credentials
```

### 2. Obtain BankID Certificates

**Test Certificates:**
```bash
# Download from BankID
wget https://www.bankid.com/assets/bankid/rp/FPTestcert4_20220818.p12

# Convert to PEM format
openssl pkcs12 -in FPTestcert4_20220818.p12 -out bankid-cert.pem -clcerts -nokeys
openssl pkcs12 -in FPTestcert4_20220818.p12 -out bankid-key.pem -nocerts -nodes

# Password: qwerty123
```

### 3. Store in AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name finnish-bankid-test-credentials \
  --secret-string file://bankid-secrets.json \
  --region eu-west-2
```

**bankid-secrets.json:**
```json
{
  "api_url": "https://appapi2.test.bankid.com/rp/v6.0",
  "cert_pem": "-----BEGIN CERTIFICATE-----\n...",
  "key_pem": "-----BEGIN PRIVATE KEY-----\n..."
}
```

### 4. Deploy Lambdas

```bash
cd templates
sam build
sam deploy --guided
```

## Testing Checklist

### Setup
- [ ] Test BankID installed on mobile device
- [ ] Test personal number obtained
- [ ] Certificates downloaded and converted
- [ ] Secrets stored in AWS Secrets Manager
- [ ] Lambdas deployed
- [ ] Lambda execution roles have Secrets Manager permissions
- [ ] Contact flow created/updated

### PII Security Testing ✅ CRITICAL
- [ ] **Verify NO PII spoken before authentication**
- [ ] Test call - listen for any customer name/DOB before BankID auth
- [ ] Verify only generic prompts play during authentication
- [ ] Confirm customer name spoken ONLY after successful auth
- [ ] Test failed auth - verify NO PII disclosed
- [ ] Test unknown caller - verify NO PII disclosed

### Authentication Flow Testing
- [ ] Test call placed from known phone number
- [ ] BankID notification received on mobile
- [ ] Authentication completed successfully
- [ ] Personalized greeting plays AFTER auth
- [ ] Contact attributes updated correctly
- [ ] Flow continues to Forethought
- [ ] Zendesk ticket created with verification flag

### Error Handling Testing
- [ ] Test authentication timeout (don't open app)
- [ ] Test authentication cancellation (cancel in app)
- [ ] Test unknown phone number (not in DB)
- [ ] Test BankID app not installed
- [ ] Verify all failures transfer to agent WITHOUT disclosing PII

## 🔒 PII Security Requirements

### Core Principle
**NEVER disclose PII before authentication is complete and verified.**

### What NOT to Do ❌

**DON'T read back customer details:**
```
❌ "I have you on record as Mona Munster, born September 22, 1985. 
    Is this correct? Press 1 to confirm."
```
**Problem:** Anyone with the customer's phone can hear their PII without proving identity.

### What TO Do ✅

**DO use generic prompts only:**
```
✅ "For security, I'm sending an authentication request to your 
    BankID app. Please check your mobile phone."
```

**DO personalize AFTER verification:**
```
✅ "Thank you, Mona. Your identity has been verified. 
    How can we help you today?"
```

### Implementation Checklist

**Before Authentication:**
- ✅ Lookup customer data silently (no voice output)
- ✅ Store in contact attributes (not spoken)
- ✅ Use only generic prompts
- ✅ Play hold music/silence during polling
- ✅ NO first names, last names, dates, or any PII

**After Successful Authentication:**
- ✅ NOW safe to use first name
- ✅ Can reference account details
- ✅ Can proceed with personalized service
- ✅ Mark contact as verified

**On Authentication Failure:**
- ✅ Generic error message only
- ✅ NO PII disclosed
- ✅ Transfer to agent for manual verification

## Production Considerations

### Security
- ✅ Use production BankID API endpoint
- ✅ Production certificates (NOT test)
- ✅ Rotate certificates before expiry
- ✅ Monitor certificate expiration dates
- ✅ Never bundle certificates in code
- ✅ Use Secrets Manager with rotation

### Performance
- ⚡ Consider timeout limits (30 seconds max for auth)
- ⚡ Implement retry logic for transient failures
- ⚡ Cache certificate loading (Lambda layers)
- ⚡ Monitor CloudWatch metrics

### User Experience
- 📱 Clear voice prompts
- 📱 Timeout handling with agent transfer
- 📱 Fallback to manual verification
- 📱 Multi-language support (Finnish/Swedish/English)

### Compliance
- 🔒 Log all authentication attempts
- 🔒 Store audit trail in CloudWatch
- 🔒 GDPR compliance for Finnish data
- 🔒 Data retention policies

## Cost Estimate

**AWS (per 1000 authentications):**
- Lambda invocations: ~$0.02
- Secrets Manager: $0.40/month
- CloudWatch Logs: ~$0.50
- **Total:** ~$0.92 per 1000 auths

**BankID:**
- Contact Finnish BankID provider for pricing
- Typically transaction-based

## Next Steps

1. [ ] Register for BankID test access
2. [ ] Install test BankID app on test device
3. [ ] Download and convert certificates
4. [ ] Deploy Lambda functions
5. [ ] Update Amazon Connect contact flow
6. [ ] Test end-to-end flow
7. [ ] Apply for production BankID access
8. [ ] Deploy to production

---

**Questions?**
- Which Finnish bank will you partner with for BankID?
- Do you need multilingual support (FI/SE/EN)?
- What's your expected authentication volume?
