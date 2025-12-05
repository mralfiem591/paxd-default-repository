// Mobile navigation toggle
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }
    
    // PaxD Webcontrol functionality
    const actionSelect = document.getElementById('action-select');
    const packageInput = document.getElementById('package-input');
    const webcontrolBtn = document.getElementById('webcontrol-btn');
    
    function updateWebcontrolButton() {
        const action = actionSelect?.value;
        const packageName = packageInput?.value.trim();
        
        if (action && packageName && webcontrolBtn) {
            webcontrolBtn.disabled = false;
            webcontrolBtn.textContent = `${action.charAt(0).toUpperCase() + action.slice(1)} ${packageName}`;
            webcontrolBtn.innerHTML = `<span class="btn-icon">🚀</span>${action.charAt(0).toUpperCase() + action.slice(1)} ${packageName}`;
        } else if (webcontrolBtn) {
            webcontrolBtn.disabled = true;
            webcontrolBtn.innerHTML = `<span class="btn-icon">🚀</span>Execute Command`;
        }
    }
    
    if (actionSelect && packageInput && webcontrolBtn) {
        actionSelect.addEventListener('change', updateWebcontrolButton);
        packageInput.addEventListener('input', updateWebcontrolButton);
        
        webcontrolBtn.addEventListener('click', function() {
            const action = actionSelect.value;
            const packageName = packageInput.value.trim();
            
            if (action && packageName) {
                const url = `paxd://${action}/${packageName}`;
                window.location.href = url;
            }
        });
    }
    
    // Let anchor links work with default browser behavior
    // Removed custom smooth scrolling to allow # links to work properly
    
    // Active navigation highlighting
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link[href^="#"]');
    
    function highlightNavigation() {
        let current = '';
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (window.pageYOffset >= (sectionTop - 200)) {
                current = section.getAttribute('id');
            }
        });
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    }
    
    window.addEventListener('scroll', highlightNavigation);
    
    // Copy code to clipboard functionality
    function addCopyButtons() {
        const codeBlocks = document.querySelectorAll('.code-content pre, .code-block pre');
        
        codeBlocks.forEach(block => {
            const wrapper = block.parentNode;
            if (wrapper.querySelector('.copy-button')) return;
            
            const copyButton = document.createElement('button');
            copyButton.className = 'copy-button';
            copyButton.innerHTML = '📋';
            copyButton.setAttribute('aria-label', 'Copy code');
            copyButton.title = 'Copy to clipboard';
            
            copyButton.addEventListener('click', async () => {
                try {
                    const code = block.textContent;
                    await navigator.clipboard.writeText(code);
                    
                    copyButton.innerHTML = '✅';
                    copyButton.style.color = '#10b981';
                    
                    setTimeout(() => {
                        copyButton.innerHTML = '📋';
                        copyButton.style.color = '';
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy code: ', err);
                    
                    // Fallback for older browsers
                    const textArea = document.createElement('textarea');
                    textArea.value = block.textContent;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    
                    copyButton.innerHTML = '✅';
                    setTimeout(() => {
                        copyButton.innerHTML = '📋';
                    }, 2000);
                }
            });
            
            wrapper.style.position = 'relative';
            wrapper.appendChild(copyButton);
        });
    }
    
    // Add copy buttons after a short delay to ensure code highlighting is complete
    setTimeout(addCopyButtons, 100);
    
    // Intersection Observer for animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Observe elements for animation
    const animatedElements = document.querySelectorAll('.feature-card, .package-card, .doc-card, .install-card');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
    
    // Enhanced mobile navigation
    function setupMobileNav() {
        const style = document.createElement('style');
        style.textContent = `
            @media (max-width: 768px) {
                .nav-menu {
                    position: fixed;
                    top: 70px;
                    left: 0;
                    width: 100%;
                    background: white;
                    flex-direction: column;
                    padding: 2rem 0;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                    transform: translateX(-100%);
                    transition: transform 0.3s ease;
                }
                
                .nav-menu.active {
                    transform: translateX(0);
                }
                
                .nav-link {
                    padding: 1rem 2rem;
                    border-bottom: 1px solid #e2e8f0;
                    width: 100%;
                    text-align: center;
                }
                
                .nav-toggle.active span:nth-child(1) {
                    transform: rotate(45deg) translate(5px, 5px);
                }
                
                .nav-toggle.active span:nth-child(2) {
                    opacity: 0;
                }
                
                .nav-toggle.active span:nth-child(3) {
                    transform: rotate(-45deg) translate(7px, -6px);
                }
            }
        `;
        document.head.appendChild(style);
        
        navToggle?.addEventListener('click', function() {
            this.classList.toggle('active');
        });
        
        // Close mobile menu when clicking a link (only for external links or when on mobile)
        document.querySelectorAll('.nav-link:not([href^="#"])').forEach(link => {
            link.addEventListener('click', () => {
                navMenu?.classList.remove('active');
                navToggle?.classList.remove('active');
            });
        });
        
        // Close mobile menu when clicking anchor links (but don't prevent default)
        document.querySelectorAll('.nav-link[href^="#"]').forEach(link => {
            link.addEventListener('click', () => {
                // Only close mobile menu, don't prevent default anchor behavior
                if (window.innerWidth <= 768) {
                    navMenu?.classList.remove('active');
                    navToggle?.classList.remove('active');
                }
            });
        });
    }
    
    setupMobileNav();
    
    // Performance optimization: lazy load images
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
});

// Add CSS for copy buttons
const copyButtonStyle = document.createElement('style');
copyButtonStyle.textContent = `
    .copy-button {
        position: absolute;
        top: 1rem;
        right: 1rem;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 0.375rem;
        color: #94a3b8;
        font-size: 0.875rem;
        padding: 0.5rem;
        cursor: pointer;
        transition: all 0.2s ease;
        backdrop-filter: blur(4px);
    }
    
    .copy-button:hover {
        background: rgba(255, 255, 255, 0.2);
        color: white;
        transform: scale(1.05);
    }
    
    .code-block .copy-button {
        background: #f1f5f9;
        color: #64748b;
        border-color: #e2e8f0;
    }
    
    .code-block .copy-button:hover {
        background: #e2e8f0;
        color: #475569;
    }
`;
document.head.appendChild(copyButtonStyle);