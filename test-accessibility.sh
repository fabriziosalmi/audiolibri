#!/bin/bash

# WCAG 2.1 AA and EN 301 549 Compliance Testing Script
# This script provides automated testing commands for accessibility compliance

echo "🔍 WCAG 2.1 AA and EN 301 549 Compliance Testing Suite"
echo "======================================================"

# Check if required tools are installed
check_tool() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 is not installed. Please install it first."
        return 1
    else
        echo "✅ $1 is available"
        return 0
    fi
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Checking required tools...${NC}"

# Check for Node.js tools
tools_available=true
if ! check_tool "npx"; then
    tools_available=false
fi

if ! check_tool "node"; then
    tools_available=false
fi

if [ "$tools_available" = false ]; then
    echo -e "${RED}Please install Node.js and npm first${NC}"
    echo "Visit: https://nodejs.org/"
    exit 1
fi

echo ""
echo -e "${BLUE}Available testing options:${NC}"
echo "1. Install accessibility testing tools"
echo "2. Run axe-core accessibility audit"
echo "3. Run Pa11y accessibility test"
echo "4. Validate HTML5"
echo "5. Test color contrast"
echo "6. Run lighthouse accessibility audit"
echo "7. Run all tests"
echo "8. Manual testing checklist"
echo "9. Exit"

read -p "Choose an option (1-9): " choice

case $choice in
    1)
        echo -e "${YELLOW}Installing accessibility testing tools...${NC}"
        npm install -g @axe-core/cli pa11y lighthouse html5-validator
        echo -e "${GREEN}Tools installed successfully!${NC}"
        ;;
    2)
        echo -e "${YELLOW}Running axe-core accessibility audit...${NC}"
        if [ -z "$1" ]; then
            echo "Please provide URL to test (e.g., http://localhost:3000)"
            read -p "Enter URL: " url
        else
            url=$1
        fi
        
        echo "Testing $url with axe-core..."
        npx @axe-core/cli $url --reporter html --output-file axe-report.html
        echo -e "${GREEN}Axe-core report generated: axe-report.html${NC}"
        ;;
    3)
        echo -e "${YELLOW}Running Pa11y accessibility test...${NC}"
        if [ -z "$1" ]; then
            echo "Please provide URL to test"
            read -p "Enter URL: " url
        else
            url=$1
        fi
        
        echo "Testing $url with Pa11y..."
        npx pa11y $url --standard WCAG2AA --reporter html > pa11y-report.html
        echo -e "${GREEN}Pa11y report generated: pa11y-report.html${NC}"
        ;;
    4)
        echo -e "${YELLOW}Validating HTML5...${NC}"
        if [ -z "$1" ]; then
            echo "Please provide URL to validate"
            read -p "Enter URL: " url
        else
            url=$1
        fi
        
        echo "Validating HTML5 for $url..."
        npx html5-validator --url $url --format text
        ;;
    5)
        echo -e "${YELLOW}Color contrast testing requires manual tools${NC}"
        echo "Recommended tools:"
        echo "- Colour Contrast Analyser: https://www.tpgi.com/color-contrast-checker/"
        echo "- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/"
        echo "- Stark (Browser extension): https://www.getstark.co/"
        ;;
    6)
        echo -e "${YELLOW}Running Lighthouse accessibility audit...${NC}"
        if [ -z "$1" ]; then
            echo "Please provide URL to test"
            read -p "Enter URL: " url
        else
            url=$1
        fi
        
        echo "Testing $url with Lighthouse..."
        npx lighthouse $url --only-categories=accessibility --output html --output-path lighthouse-accessibility-report.html
        echo -e "${GREEN}Lighthouse report generated: lighthouse-accessibility-report.html${NC}"
        ;;
    7)
        echo -e "${YELLOW}Running all automated tests...${NC}"
        if [ -z "$1" ]; then
            echo "Please provide URL to test"
            read -p "Enter URL: " url
        else
            url=$1
        fi
        
        echo "Running comprehensive accessibility testing for $url..."
        
        # Run axe-core
        echo "1/4 Running axe-core..."
        npx @axe-core/cli $url --reporter html --output-file axe-report.html
        
        # Run Pa11y
        echo "2/4 Running Pa11y..."
        npx pa11y $url --standard WCAG2AA --reporter html > pa11y-report.html
        
        # Validate HTML
        echo "3/4 Validating HTML..."
        npx html5-validator --url $url --format text > html-validation.txt
        
        # Run Lighthouse
        echo "4/4 Running Lighthouse..."
        npx lighthouse $url --only-categories=accessibility --output html --output-path lighthouse-accessibility-report.html
        
        echo -e "${GREEN}All tests completed! Reports generated:${NC}"
        echo "- axe-report.html"
        echo "- pa11y-report.html"
        echo "- html-validation.txt"
        echo "- lighthouse-accessibility-report.html"
        ;;
    8)
        echo -e "${BLUE}Manual Testing Checklist for WCAG 2.1 AA and EN 301 549${NC}"
        echo "================================================================"
        echo ""
        echo -e "${YELLOW}Keyboard Navigation:${NC}"
        echo "□ Tab through all interactive elements"
        echo "□ Verify logical tab order"
        echo "□ Test keyboard shortcuts (Alt+H, Alt+M, Alt+S)"
        echo "□ Ensure no keyboard traps"
        echo "□ Verify skip link works (Tab from page load)"
        echo "□ Test Escape key functionality"
        echo ""
        echo -e "${YELLOW}Screen Reader Testing:${NC}"
        echo "□ Test with NVDA (Windows)"
        echo "□ Test with VoiceOver (macOS/iOS)"
        echo "□ Test with TalkBack (Android)"
        echo "□ Verify all content is announced"
        echo "□ Check aria-live regions work"
        echo "□ Test form labeling"
        echo ""
        echo -e "${YELLOW}Visual Testing:${NC}"
        echo "□ Test at 200% zoom level"
        echo "□ Test at 400% zoom level (EN 301 549 requirement)"
        echo "□ Verify focus indicators are visible"
        echo "□ Test high contrast mode"
        echo "□ Check color contrast ratios"
        echo "□ Test without CSS"
        echo ""
        echo -e "${YELLOW}Mobile Testing:${NC}"
        echo "□ Test on actual mobile devices"
        echo "□ Verify touch targets are at least 44px"
        echo "□ Test portrait and landscape orientations"
        echo "□ Test with mobile screen readers"
        echo "□ Verify swipe gestures work"
        echo ""
        echo -e "${YELLOW}User Preference Testing:${NC}"
        echo "□ Test with reduced motion enabled"
        echo "□ Test with high contrast enabled"
        echo "□ Test with large text settings"
        echo "□ Test with dark mode"
        echo "□ Test with browser zoom"
        echo ""
        echo -e "${YELLOW}Content Testing:${NC}"
        echo "□ Verify all images have alt text"
        echo "□ Check heading structure (H1→H2→H3)"
        echo "□ Test form error handling"
        echo "□ Verify language attributes"
        echo "□ Check for proper semantic markup"
        echo ""
        echo -e "${YELLOW}EN 301 549 Specific:${NC}"
        echo "□ Test session timeout warnings"
        echo "□ Verify error message accessibility"
        echo "□ Test keyboard shortcut announcements"
        echo "□ Check multi-language preparation"
        echo "□ Verify cognitive accessibility features"
        echo ""
        echo -e "${GREEN}Testing Tools:${NC}"
        echo "- axe DevTools browser extension"
        echo "- WAVE browser extension"
        echo "- Colour Contrast Analyser"
        echo "- Screen readers (NVDA, VoiceOver, TalkBack)"
        echo "- Browser developer tools"
        ;;
    9)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid option. Please choose 1-9.${NC}"
        ;;
esac

echo ""
echo -e "${BLUE}Additional Resources:${NC}"
echo "- WCAG 2.1 Quick Reference: https://www.w3.org/WAI/WCAG21/quickref/"
echo "- EN 301 549 Standard: https://www.etsi.org/deliver/etsi_en/301500_301599/301549/"
echo "- WebAIM Resources: https://webaim.org/"
echo "- axe-core GitHub: https://github.com/dequelabs/axe-core"
