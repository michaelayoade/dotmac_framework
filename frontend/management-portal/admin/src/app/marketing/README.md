# DotMac Platform Website

Modern, responsive website for the DotMac Platform - a strategic ISP management platform with plugin-based DNS automation.

## 🌟 Features

- **Responsive Design** - Works perfectly on desktop, tablet, and mobile
- **Modern UI/UX** - Clean, professional design with Tailwind CSS
- **Interactive Documentation** - Complete API reference and deployment guides
- **Strategic Messaging** - Focuses on leveraging existing infrastructure
- **Plugin Architecture Showcase** - Highlights vendor-neutral approach

## 🚀 Quick Start

### Option 1: Simple Python Server (Recommended)

```bash
cd /home/dotmac-website
python3 serve.py
```

This will:
- Start a local web server on http://localhost:8080
- Automatically open your browser
- Provide proper MIME types and CORS headers

### Option 2: Python's Built-in Server

```bash
cd /home/dotmac-website
python3 -m http.server 8080
```

### Option 3: Node.js (if available)

```bash
cd /home/dotmac-website
npx serve . -p 8080
```

## 📁 Structure

```
/home/dotmac-website/
├── index.html                              # Main landing page
├── docs/
│   ├── strategic-dns-deployment.html       # DNS deployment guide
│   ├── api-reference.html                  # Complete API documentation
│   ├── plugin-development.html             # Plugin development guide
│   └── ...                                 # Additional documentation
├── assets/
│   ├── css/                                # Custom stylesheets
│   ├── js/                                 # JavaScript files
│   └── images/                             # Images and screenshots
├── serve.py                                # Local development server
└── README.md                               # This file
```

## 🎨 Design Features

### Landing Page (index.html)
- **Hero Section** - Eye-catching gradient with key value proposition
- **Benefits Overview** - Strategic infrastructure usage highlights
- **Feature Showcase** - Complete ISP management suite
- **Architecture Explanation** - Plugin-based approach
- **Deployment Strategies** - Multiple infrastructure options
- **Quick Start Guide** - Step-by-step deployment
- **Documentation Links** - Easy access to guides

### Documentation Pages
- **Strategic DNS Deployment** - Complete infrastructure leverage guide
- **API Reference** - Interactive API documentation with examples
- **Plugin Development** - How to extend the platform
- **Security & Compliance** - Enterprise security features

### Technical Features
- **Tailwind CSS** - Modern, responsive styling
- **Prism.js** - Syntax highlighting for code blocks
- **Smooth Scrolling** - Enhanced navigation experience
- **Mobile Responsive** - Works on all device sizes
- **Fast Loading** - Optimized assets and CDN usage

## 🔧 Customization

### Branding
Update the logo and brand colors in `index.html`:

```html
<!-- Logo/Brand -->
<div class="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center">
    <span class="text-white font-bold text-lg">D</span>
</div>

<!-- Update gradient colors -->
<style>
.gradient-bg {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
```

### Content
- Update company information in the footer
- Modify the GitHub links to point to your repository
- Customize the deployment examples with your domains
- Add your own screenshots and demos

### Styling
The site uses Tailwind CSS loaded from CDN. For custom styles:

1. Add custom CSS in the `<style>` section of each HTML file
2. Or create separate CSS files in `assets/css/`

## 🌐 Deployment

### GitHub Pages

1. Create a repository for the website
2. Upload all files from `/home/dotmac-website/`
3. Enable GitHub Pages in repository settings
4. Choose "Deploy from branch" and select `main`

### Netlify

1. Create a new site from the website directory
2. Build command: (none needed - static site)
3. Publish directory: `.`
4. Deploy!

### Your Own Server

```bash
# Copy website files to your web server
scp -r /home/dotmac-website/* user@yourserver:/var/www/html/

# Or use nginx/apache to serve the files
```

## 📱 Mobile Responsiveness

The website is fully responsive with breakpoints for:
- **Mobile**: < 640px
- **Tablet**: 640px - 1024px  
- **Desktop**: > 1024px

All components automatically adapt to screen size.

## 🎯 SEO Optimized

- Meta descriptions for search engines
- Semantic HTML structure
- Fast loading times
- Mobile-friendly design
- Structured data ready

## 🔗 Integration with DotMac Platform

The website includes:
- **Live API Examples** - Real endpoint documentation
- **Deployment Scripts** - Actual command examples
- **Configuration Samples** - Production-ready configs
- **Strategic Guidance** - Best practices for infrastructure

## 🤝 Contributing

To update the website:

1. Edit the HTML files directly
2. Test locally with `python3 serve.py`
3. Deploy to your hosting platform
4. Update documentation as the platform evolves

## 📞 Support

- **Platform Issues**: See the main DotMac Platform repository
- **Website Issues**: Check browser console and server logs
- **Feature Requests**: Create issues in the main repository

---

**Built with ❤️ for the DotMac Platform community**