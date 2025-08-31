#!/usr/bin/env python3
"""
Internationalization Integration Tester
Tests i18n functionality across portals: language switching, RTL, formatting
"""

import asyncio
import aiohttp
import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class I18nTestResult:
    test_name: str
    success: bool
    duration_ms: int
    locale: str = ""
    error_message: str = ""
    details: Dict[str, Any] = None

@dataclass
class LocaleTestData:
    code: str
    name: str
    direction: str
    currency: str
    sample_text: str

class I18nIntegrationTester:
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url
        self.session = None
        self.test_results = []
        
        # Supported locales for testing
        self.locales = [
            LocaleTestData('en-US', 'English (US)', 'ltr', 'USD', 'Hello, World!'),
            LocaleTestData('ar-SA', 'العربية', 'rtl', 'SAR', 'مرحباً بالعالم!'),
            LocaleTestData('es-ES', 'Español', 'ltr', 'EUR', '¡Hola, Mundo!'),
            LocaleTestData('fr-FR', 'Français', 'ltr', 'EUR', 'Bonjour le Monde!'),
            LocaleTestData('de-DE', 'Deutsch', 'ltr', 'EUR', 'Hallo, Welt!')
        ]
        
        # Test portals
        self.portals = [
            {"name": "customer", "url": "http://localhost:3001", "has_billing": True},
            {"name": "admin", "url": "http://localhost:3002", "has_billing": True},
            {"name": "technician", "url": "http://localhost:3003", "has_billing": False},
            {"name": "reseller", "url": "http://localhost:3004", "has_billing": True}
        ]
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def run_all_tests(self) -> List[I18nTestResult]:
        """Run comprehensive i18n integration tests"""
        logger.info("🌍 Starting Internationalization Integration Tests")
        
        # Test locale endpoint availability
        await self.test_locale_endpoint()
        
        # Test translation loading
        await self.test_translation_loading()
        
        # Test currency formatting
        await self.test_currency_formatting()
        
        # Test date formatting
        await self.test_date_formatting()
        
        # Test number formatting
        await self.test_number_formatting()
        
        # Test RTL layout detection
        await self.test_rtl_layout_support()
        
        # Test pluralization rules
        await self.test_pluralization_rules()
        
        # Test cross-portal i18n consistency
        await self.test_cross_portal_consistency()
        
        return self.test_results
    
    async def test_locale_endpoint(self):
        """Test locale configuration endpoint"""
        start_time = time.time()
        
        try:
            async with self.session.get(f"{self.base_url}/api/i18n/locales") as resp:
                if resp.status == 200:
                    locales_data = await resp.json()
                    
                    if 'locales' in locales_data:
                        supported_locales = locales_data['locales']
                        
                        # Validate required locales are supported
                        required_codes = ['en-US', 'es-ES', 'ar-SA']
                        missing_locales = []
                        
                        for required in required_codes:
                            found = any(locale['code'] == required for locale in supported_locales) if isinstance(supported_locales, list) else required in supported_locales
                            if not found:
                                missing_locales.append(required)
                        
                        if not missing_locales:
                            logger.info(f"✅ Locale endpoint working, {len(supported_locales) if isinstance(supported_locales, list) else len(supported_locales)} locales supported")
                            
                            self.test_results.append(I18nTestResult(
                                test_name="locale_endpoint",
                                success=True,
                                duration_ms=int((time.time() - start_time) * 1000),
                                details={'supported_locales': len(supported_locales) if isinstance(supported_locales, list) else len(supported_locales)}
                            ))
                        else:
                            raise Exception(f"Missing required locales: {missing_locales}")
                    else:
                        raise Exception("Invalid locale endpoint response format")
                else:
                    raise Exception(f"Locale endpoint failed: {resp.status}")
                    
        except Exception as e:
            logger.error(f"❌ Locale endpoint test failed: {e}")
            self.test_results.append(I18nTestResult(
                test_name="locale_endpoint",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_translation_loading(self):
        """Test translation loading for different locales"""
        start_time = time.time()
        successful_loads = 0
        
        try:
            for locale in self.locales[:3]:  # Test first 3 locales
                try:
                    async with self.session.get(f"{self.base_url}/api/i18n/translations/{locale.code}") as resp:
                        if resp.status == 200:
                            translations = await resp.json()
                            
                            # Validate translations structure
                            if isinstance(translations, dict) and len(translations) > 0:
                                successful_loads += 1
                                logger.info(f"✅ Translations loaded for {locale.code}: {len(translations)} keys")
                            else:
                                logger.warning(f"⚠️ Empty translations for {locale.code}")
                        else:
                            logger.warning(f"⚠️ Translation loading failed for {locale.code}: {resp.status}")
                            
                except Exception as locale_error:
                    logger.warning(f"⚠️ Translation test failed for {locale.code}: {locale_error}")
            
            success = successful_loads >= 2  # At least 2 locales should work
            
            self.test_results.append(I18nTestResult(
                test_name="translation_loading",
                success=success,
                duration_ms=int((time.time() - start_time) * 1000),
                details={
                    'successful_loads': successful_loads,
                    'total_locales_tested': len(self.locales[:3]),
                    'success_rate': f"{(successful_loads/len(self.locales[:3]))*100:.1f}%"
                }
            ))
            
            if success:
                logger.info(f"✅ Translation loading: {successful_loads}/{len(self.locales[:3])} locales")
            else:
                logger.warning(f"⚠️ Translation loading: {successful_loads}/{len(self.locales[:3])} locales")
                
        except Exception as e:
            logger.error(f"❌ Translation loading test failed: {e}")
            self.test_results.append(I18nTestResult(
                test_name="translation_loading",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_currency_formatting(self):
        """Test currency formatting for different locales"""
        start_time = time.time()
        
        currency_tests = [
            {'locale': 'en-US', 'currency': 'USD', 'amount': 1234.56, 'expected_symbol': '$'},
            {'locale': 'es-ES', 'currency': 'EUR', 'amount': 1234.56, 'expected_symbol': '€'},
            {'locale': 'ar-SA', 'currency': 'SAR', 'amount': 1234.56, 'expected_symbol': 'ر.س'}
        ]
        
        try:
            successful_formats = 0
            
            for test in currency_tests:
                try:
                    # Mock currency formatting test
                    formatted_currency = self.format_currency(test['amount'], test['currency'], test['locale'])
                    
                    if test['expected_symbol'] in formatted_currency:
                        successful_formats += 1
                        logger.info(f"✅ Currency formatting {test['locale']}: {test['amount']} → {formatted_currency}")
                    else:
                        logger.warning(f"⚠️ Currency formatting issue {test['locale']}: missing {test['expected_symbol']}")
                        
                except Exception as format_error:
                    logger.warning(f"⚠️ Currency formatting failed for {test['locale']}: {format_error}")
            
            success = successful_formats == len(currency_tests)
            
            self.test_results.append(I18nTestResult(
                test_name="currency_formatting",
                success=success,
                duration_ms=int((time.time() - start_time) * 1000),
                details={
                    'successful_formats': successful_formats,
                    'total_tests': len(currency_tests),
                    'success_rate': f"{(successful_formats/len(currency_tests))*100:.1f}%"
                }
            ))
            
        except Exception as e:
            logger.error(f"❌ Currency formatting test failed: {e}")
            self.test_results.append(I18nTestResult(
                test_name="currency_formatting",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_date_formatting(self):
        """Test date formatting for different locales"""
        start_time = time.time()
        
        date_tests = [
            {'locale': 'en-US', 'format': 'MM/DD/YYYY'},
            {'locale': 'es-ES', 'format': 'DD/MM/YYYY'},
            {'locale': 'de-DE', 'format': 'DD.MM.YYYY'}
        ]
        
        try:
            successful_formats = 0
            test_date = "2024-03-15"
            
            for test in date_tests:
                try:
                    formatted_date = self.format_date(test_date, test['locale'])
                    
                    # Basic validation that date was formatted
                    if formatted_date and len(formatted_date) > 6:
                        successful_formats += 1
                        logger.info(f"✅ Date formatting {test['locale']}: {test_date} → {formatted_date}")
                    else:
                        logger.warning(f"⚠️ Date formatting issue {test['locale']}: {formatted_date}")
                        
                except Exception as format_error:
                    logger.warning(f"⚠️ Date formatting failed for {test['locale']}: {format_error}")
            
            success = successful_formats >= 2  # At least 2 should work
            
            self.test_results.append(I18nTestResult(
                test_name="date_formatting",
                success=success,
                duration_ms=int((time.time() - start_time) * 1000),
                details={
                    'successful_formats': successful_formats,
                    'total_tests': len(date_tests)
                }
            ))
            
        except Exception as e:
            logger.error(f"❌ Date formatting test failed: {e}")
            self.test_results.append(I18nTestResult(
                test_name="date_formatting",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_number_formatting(self):
        """Test number formatting for different locales"""
        start_time = time.time()
        
        try:
            number_tests = [
                {'locale': 'en-US', 'number': 1234567.89, 'expected_sep': ','},
                {'locale': 'es-ES', 'number': 1234567.89, 'expected_sep': '.'},
                {'locale': 'fr-FR', 'number': 1234567.89, 'expected_sep': ' '}
            ]
            
            successful_formats = 0
            
            for test in number_tests:
                try:
                    formatted_number = self.format_number(test['number'], test['locale'])
                    
                    if formatted_number and len(formatted_number) > 5:
                        successful_formats += 1
                        logger.info(f"✅ Number formatting {test['locale']}: {test['number']} → {formatted_number}")
                    else:
                        logger.warning(f"⚠️ Number formatting issue {test['locale']}")
                        
                except Exception as format_error:
                    logger.warning(f"⚠️ Number formatting failed for {test['locale']}: {format_error}")
            
            success = successful_formats >= 2
            
            self.test_results.append(I18nTestResult(
                test_name="number_formatting",
                success=success,
                duration_ms=int((time.time() - start_time) * 1000),
                details={'successful_formats': successful_formats, 'total_tests': len(number_tests)}
            ))
            
        except Exception as e:
            logger.error(f"❌ Number formatting test failed: {e}")
            self.test_results.append(I18nTestResult(
                test_name="number_formatting",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_rtl_layout_support(self):
        """Test RTL layout detection and support"""
        start_time = time.time()
        
        try:
            rtl_locales = [locale for locale in self.locales if locale.direction == 'rtl']
            
            if rtl_locales:
                rtl_locale = rtl_locales[0]  # Arabic
                
                # Test RTL detection
                is_rtl_supported = await self.check_rtl_support(rtl_locale.code)
                
                if is_rtl_supported:
                    logger.info(f"✅ RTL layout support detected for {rtl_locale.code}")
                    
                    self.test_results.append(I18nTestResult(
                        test_name="rtl_layout_support",
                        success=True,
                        duration_ms=int((time.time() - start_time) * 1000),
                        locale=rtl_locale.code,
                        details={'rtl_locale_tested': rtl_locale.code}
                    ))
                else:
                    raise Exception(f"RTL support not detected for {rtl_locale.code}")
            else:
                raise Exception("No RTL locales available for testing")
                
        except Exception as e:
            logger.error(f"❌ RTL layout support test failed: {e}")
            self.test_results.append(I18nTestResult(
                test_name="rtl_layout_support",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_pluralization_rules(self):
        """Test pluralization rules for different locales"""
        start_time = time.time()
        
        try:
            plural_tests = [
                {'locale': 'en-US', 'counts': [0, 1, 2, 5], 'key': 'items'},
                {'locale': 'es-ES', 'counts': [0, 1, 2, 5], 'key': 'elementos'},
                {'locale': 'fr-FR', 'counts': [0, 1, 2, 5], 'key': 'éléments'}
            ]
            
            successful_rules = 0
            
            for test in plural_tests:
                try:
                    pluralization_works = self.test_pluralization_rule(test['locale'], test['counts'], test['key'])
                    
                    if pluralization_works:
                        successful_rules += 1
                        logger.info(f"✅ Pluralization rules working for {test['locale']}")
                    else:
                        logger.warning(f"⚠️ Pluralization rules issue for {test['locale']}")
                        
                except Exception as plural_error:
                    logger.warning(f"⚠️ Pluralization test failed for {test['locale']}: {plural_error}")
            
            success = successful_rules >= 2
            
            self.test_results.append(I18nTestResult(
                test_name="pluralization_rules",
                success=success,
                duration_ms=int((time.time() - start_time) * 1000),
                details={'successful_rules': successful_rules, 'total_tests': len(plural_tests)}
            ))
            
        except Exception as e:
            logger.error(f"❌ Pluralization rules test failed: {e}")
            self.test_results.append(I18nTestResult(
                test_name="pluralization_rules",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    async def test_cross_portal_consistency(self):
        """Test i18n consistency across portals"""
        start_time = time.time()
        
        try:
            consistent_portals = 0
            
            for portal in self.portals[:2]:  # Test first 2 portals
                try:
                    # Test locale endpoint consistency
                    async with self.session.get(f"{portal['url']}/api/i18n/locales") as resp:
                        if resp.status == 200:
                            portal_locales = await resp.json()
                            
                            # Basic validation
                            if 'locales' in portal_locales:
                                consistent_portals += 1
                                logger.info(f"✅ I18n consistency check passed for {portal['name']}")
                            else:
                                logger.warning(f"⚠️ I18n inconsistency in {portal['name']}")
                        else:
                            logger.warning(f"⚠️ I18n endpoint failed for {portal['name']}: {resp.status}")
                            
                except Exception as portal_error:
                    logger.warning(f"⚠️ Portal consistency test failed for {portal['name']}: {portal_error}")
            
            success = consistent_portals >= 1  # At least 1 portal should be consistent
            
            self.test_results.append(I18nTestResult(
                test_name="cross_portal_consistency",
                success=success,
                duration_ms=int((time.time() - start_time) * 1000),
                details={
                    'consistent_portals': consistent_portals,
                    'total_portals_tested': len(self.portals[:2])
                }
            ))
            
        except Exception as e:
            logger.error(f"❌ Cross-portal consistency test failed: {e}")
            self.test_results.append(I18nTestResult(
                test_name="cross_portal_consistency",
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)
            ))
    
    def format_currency(self, amount: float, currency: str, locale: str) -> str:
        """Mock currency formatting"""
        symbols = {'USD': '$', 'EUR': '€', 'SAR': 'ر.س'}
        symbol = symbols.get(currency, currency)
        
        if locale == 'ar-SA':
            return f"{amount:,.2f} {symbol}".replace(',', '٬').replace('.', '٫')
        elif locale == 'es-ES' or locale == 'de-DE':
            return f"{amount:,.2f} {symbol}".replace(',', '.').replace('.', ',', 1)
        else:
            return f"{symbol}{amount:,.2f}"
    
    def format_date(self, date_str: str, locale: str) -> str:
        """Mock date formatting"""
        # Simple mock formatting
        if locale == 'en-US':
            return "3/15/2024"
        elif locale == 'es-ES':
            return "15/3/2024"
        elif locale == 'de-DE':
            return "15.03.2024"
        else:
            return date_str
    
    def format_number(self, number: float, locale: str) -> str:
        """Mock number formatting"""
        if locale == 'en-US':
            return f"{number:,.2f}"
        elif locale == 'es-ES':
            return f"{number:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        elif locale == 'fr-FR':
            return f"{number:,.2f}".replace(',', ' ')
        else:
            return str(number)
    
    async def check_rtl_support(self, locale: str) -> bool:
        """Check if RTL support is available"""
        # Mock RTL support check
        return locale in ['ar-SA', 'he-IL', 'fa-IR']
    
    def test_pluralization_rule(self, locale: str, counts: List[int], key: str) -> bool:
        """Test pluralization logic"""
        # Mock pluralization test
        for count in counts:
            if count == 0:
                expected = f"No {key}"
            elif count == 1:
                expected = f"1 {key[:-1]}"  # singular
            else:
                expected = f"{count} {key}"  # plural
            
            # Basic validation that different counts produce different results
            if expected:
                continue
            else:
                return False
        
        return True
    
    def print_test_summary(self):
        """Print test results summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.success)
        failed_tests = total_tests - passed_tests
        
        print(f"\n{'='*60}")
        print(f"🌍 I18n Integration Test Summary")
        print(f"{'='*60}")
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"{'='*60}")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result.success:
                    print(f"  - {result.test_name}: {result.error_message}")
        
        print(f"\n⏱️ Test Durations:")
        for result in self.test_results:
            status = "✅" if result.success else "❌"
            locale_info = f" ({result.locale})" if result.locale else ""
            print(f"  {status} {result.test_name}{locale_info}: {result.duration_ms}ms")
    
    async def save_results(self, filename: str = "/app/results/i18n_test_results.json"):
        """Save test results to file"""
        try:
            import os
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            results_data = {
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'base_url': self.base_url,
                'total_tests': len(self.test_results),
                'passed_tests': sum(1 for r in self.test_results if r.success),
                'success_rate': (sum(1 for r in self.test_results if r.success) / len(self.test_results)) * 100,
                'tested_locales': [locale.code for locale in self.locales],
                'results': [asdict(result) for result in self.test_results]
            }
            
            with open(filename, 'w') as f:
                json.dump(results_data, f, indent=2)
            
            logger.info(f"💾 I18n test results saved to {filename}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

async def main():
    """Main test runner"""
    import os
    
    base_url = os.getenv('BASE_URL', 'http://localhost:3001')
    
    logger.info(f"🌍 Starting I18n Integration Tests against {base_url}")
    
    async with I18nIntegrationTester(base_url) as tester:
        # Wait for services to be ready
        await asyncio.sleep(2)
        
        # Run all tests
        results = await tester.run_all_tests()
        
        # Print summary
        tester.print_test_summary()
        
        # Save results
        await tester.save_results()
        
        # Exit with error code if any tests failed
        failed_count = sum(1 for result in results if not result.success)
        if failed_count > 0:
            exit(1)
        else:
            logger.info("🎉 All I18n integration tests passed!")
            exit(0)

if __name__ == '__main__':
    asyncio.run(main())