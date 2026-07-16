# BankID Integration with Amazon Connect - Implementation Plan

## Overview
Integrate BankID authentication into your existing Amazon Connect + Forethought + Zendesk workflow.

## Architecture

```
Customer Call → Connect Flow
                    ↓
            [BankID Authentication Lambda]
                    ↓
            [fetchCustomerData Lambda]
                    ↓
            [Update Contact Attributes]
                    ↓
            [forethoughtPostLambda] → Forethought Bot
                    ↓
            [Transfer to Queue/Agent]
```

## Components Needed

### 1. BankID Authentication Lambda
**Function Name:** `bankIDAuthenticateLambda`

**Purpose:** Authenticate customer via BankID and return customer details

**Inputs (from Connect):**
- Phone number (from caller ID)
- Personal number (DTMF input or pre-populated)
- BankID method (mobile/same-device)

**Outputs:**
- Authentication status (success/failed)
- Customer name (first_name, last_name)
- Date of birth
- BankID unique identifier
- Authentication timestamp

### 2. Contact Flow Updates

**New Flow: "BankID Authentication Flow"**

```
1. Play prompt: "Welcome. For security, we need to verify your identity."
2. Get customer input: "Please enter your personal number"
3. Invoke Lambda: bankIDAuthenticateLambda
4. Check conditions:
   - If authentication_status = "success"
     → Set contact attributes (first_name, last_name, date_of_birth, verified=true)
     → Continue to fetchCustomerData
   - If authentication_status = "failed"
     → Play prompt: "Authentication failed. Transferring to agent."
     → Transfer to queue
5. Continue existing flow...
```

### 3. Integration Points

#### A. Update Contact Attributes Block
**After BankID Lambda, before forethoughtPostLambda:**

```json
{
  "Attributes": {
    "email": "$.External.email",
    "first_name": "$.External.first_name",
    "last_name": "$.External.last_name",
    "patient_id": "$.External.patient_id",
    "date_of_birth": "$.External.date_of_birth",
    "language": "en",
    "country": "Sweden",
    "caller_type": "private",
    "bankid_verified": "$.External.verified",
    "bankid_unique_id": "$.External.bankid_unique_id"
  }
}
```

#### B. Zendesk Custom Fields
Create new Zendesk custom fields:
- **BankID Verified** (checkbox)
- **BankID Unique ID** (text)
- **BankID Verification Timestamp** (date/time)

Map these to Forethought Context Variables so they populate in tickets.

## Deployment Steps

### Phase 1: Test Environment Setup

1. **Get BankID Test Credentials**
   - Register at demo.bankid.com (Sweden) or developer.bankid.cz (Czech)
   - Download test certificates
   - Install test mobile app
   - Create test users

2. **Store Secrets in AWS Secrets Manager**
   ```bash
   aws secretsmanager create-secret \
     --name bankid-test-credentials \
     --secret-string '{
       "api_url": "https://appapi2.test.bankid.com/rp/v6.0",
       "client_id": "your-client-id",
       "cert_pem": "-----BEGIN CERTIFICATE-----...",
       "key_pem": "-----BEGIN PRIVATE KEY-----..."
     }' \
     --region eu-west-2
   ```

3. **Deploy BankID Lambda**
   ```bash
   cd templates
   sam build
   sam deploy --guided
   ```

4. **Create Contact Flow**
   - Import/create BankID authentication flow
   - Test with test BankID credentials

5. **Update Forethought Context Variables**
   - Add `bankid_verified` CV
   - Add `bankid_unique_id` CV
   - Get UUIDs

6. **Test End-to-End**
   - Call test number
   - Authenticate via BankID test app
   - Verify data flows to Forethought
   - Check Zendesk ticket creation

### Phase 2: Production Deployment

1. **Get Production BankID Credentials**
   - Apply for production access
   - Obtain production certificates
   - Complete compliance requirements

2. **Deploy to Production**
   - Update Lambda environment variables
   - Point to production secrets
   - Deploy contact flow
   - Monitor CloudWatch logs

3. **Security Hardening**
   - Enable certificate rotation
   - Set up CloudWatch alarms for auth failures
   - Implement rate limiting
   - Add audit logging

## Testing Checklist

- [ ] BankID test account created
- [ ] Test certificates installed
- [ ] Lambda deployed to test environment
- [ ] Contact flow configured
- [ ] Successful authentication flow tested
- [ ] Failed authentication flow tested
- [ ] Timeout scenarios tested
- [ ] Data flowing to Forethought verified
- [ ] Zendesk ticket creation verified
- [ ] CloudWatch logs reviewed
- [ ] Error handling tested
- [ ] Security review completed

## Support Resources

- **Swedish BankID Docs:** https://developers.bankid.com/
- **Czech Bank iD Docs:** https://developer.bankid.cz/
- **AWS Sample:** https://github.com/aws-samples/amazon-connect-with-bankid-integration
- **BankID Support:** (check provider documentation)

## Next Steps

1. **Decide which BankID system** (Swedish vs Czech)
2. **Register for test access**
3. **Review and approve this plan**
4. **Set up development environment**
5. **Begin Phase 1 implementation**
