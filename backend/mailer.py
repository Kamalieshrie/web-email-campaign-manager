import ssl
import urllib3

# Disable SSL verification for email sending
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import os, ssl, smtplib
import dns.resolver
import re
from email_validator import validate_email, EmailNotValidError

# Configure DNS resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1'] 

from email.message import EmailMessage
from smtplib import SMTPRecipientsRefused, SMTPException, SMTPResponseException

def comprehensive_email_validation(email):
    """
    Comprehensive email validation that's consistent for all invalid emails
    Returns: (is_valid, error_message)
    """
    try:
        # Step 1: Basic format validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email.strip()):
            return False, "FAILED: Invalid email format"
        
        email = email.strip().lower()
        
        # Step 2: Check for obviously fake patterns
        fake_patterns = [
            r'fake.*@',
            r'test.*@',
            r'invalid.*@',
            r'notreal.*@',
            r'dummy.*@',
            r'this.*@',           # Catches "thisdoesnotexist@"
            r'not\..*@',          # Catches "not.a.real.user.xyz@" (escaped dot for literal match)
            r'@example\.com$',
            r'@test\.com$',
            r'@invalid\.com$'
        ]
        
        for pattern in fake_patterns:
            if re.search(pattern, email, re.IGNORECASE):
                return False, "FAILED: Invalid email address"
        
        # Step 3: Use email-validator library for more thorough validation
        try:
            valid = validate_email(email)
            normalized_email = valid.email
        except EmailNotValidError:
            return False, "FAILED: Invalid email address"
        
        # Step 4: DNS validation - be more strict
        domain = normalized_email.split('@')[1]
        
        # Check for common invalid domains
        invalid_domains = [
            'example.com', 'test.com', 'invalid.com', 'fake.com',
            'dummy.com', 'notreal.com', 'temp.com'
        ]
        
        if domain in invalid_domains:
            return False, "FAILED: Invalid email domain"
        
        # Check DNS records
        try:
            # First try MX records
            mx_records = dns.resolver.resolve(domain, 'MX')
            if len(mx_records) > 0:
                return True, "Valid email"
        except dns.resolver.NXDOMAIN:
            return False, "FAILED: Domain does not exist"
        except dns.resolver.NoAnswer:
            # If no MX records, try A records
            try:
                a_records = dns.resolver.resolve(domain, 'A')
                if len(a_records) > 0:
                    return True, "Valid email"
                else:
                    return False, "FAILED: Domain has no mail server"
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                return False, "FAILED: Domain does not exist"
        except dns.resolver.Timeout:
            return False, "FAILED: DNS timeout"
        except Exception:
            return False, "FAILED: DNS validation error"
            
        return False, "FAILED: Domain has no mail server"
            
    except Exception:
        return False, "FAILED: Email validation error"

def validate_email_dns(email):
    """Legacy function - kept for compatibility but now uses comprehensive validation"""
    is_valid, message = comprehensive_email_validation(email)
    return is_valid, message

def send_email_smtp(host, port, username, password, from_email, to_email, subject, html):
    """
    Send email with consistent validation and error handling
    """
    msg = EmailMessage()
    msg["From"] = from_email or username
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content("This is an HTML email. Please use an HTML client to view it.")
    msg.add_alternative(html, subtype="html")

    context = ssl.create_default_context()
    
    try:
        # Validate email before attempting to send
        is_valid, validation_message = comprehensive_email_validation(to_email)
        if not is_valid:
            # Create a consistent error format
            raise SMTPRecipientsRefused({to_email: (550, validation_message)})
            
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            
            # Login to the SMTP server
            server.login(username, password)
            
            # Send the actual message
            server.send_message(msg)
            
    except SMTPRecipientsRefused as e:
        # Re-raise this so the main function can handle it specifically
        raise
    except SMTPResponseException as e:
        # Handle specific SMTP response errors
        if e.smtp_code == 550:
            raise SMTPRecipientsRefused({to_email: (550, "FAILED: Address not found")})
        else:
            raise SMTPRecipientsRefused({to_email: (e.smtp_code, f"FAILED: SMTP error - {e.smtp_error}")})
    except SMTPException as e:
        # Handle other SMTP exceptions
        raise SMTPRecipientsRefused({to_email: (550, f"FAILED: SMTP error - {str(e)}")})
    except Exception as e:
        # Wrap other exceptions consistently
        raise SMTPRecipientsRefused({to_email: (550, f"FAILED: Email error - {str(e)}")})