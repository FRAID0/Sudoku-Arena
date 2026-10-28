/**
 * ============================================================================
 * 🎮 SUDOKU ARENA — ANIMATIONS & IMMERSIVE ENGINE
 * GSAP + HTML5 Canvas Cyberpunk Mesh + Caster Equalizer + UI Juice
 * ============================================================================
 */

(function () {
    'use strict';

    // ========================================================================
    // 1. PARTICLES CANVAS ENGINE (Cyberpunk Network Mesh)
    // ========================================================================
    const canvas = document.getElementById('particleCanvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        let width = 0;
        let height = 0;
        let particles = [];
        let mouse = { x: -9999, y: -9999, radius: 120 };
        let animationFrameId = null;

        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        function resizeCanvas() {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
            initParticles();
        }

        function initParticles() {
            particles = [];
            if (prefersReducedMotion) return;

            // Nombre de particules adapté à la taille de l'écran (mobile vs desktop)
            const count = Math.min(Math.floor((width * height) / 18000), 70);

            for (let i = 0; i < count; i++) {
                particles.push({
                    x: Math.random() * width,
                    y: Math.random() * height,
                    vx: (Math.random() - 0.5) * 0.45,
                    vy: (Math.random() - 0.5) * 0.45,
                    radius: Math.random() * 2 + 1,
                    baseAlpha: Math.random() * 0.4 + 0.2,
                    hue: Math.random() > 0.6 ? 188 : (Math.random() > 0.5 ? 275 : 210) // Cyan, Violet, Bleu
                });
            }
        }

        function drawParticles() {
            ctx.clearRect(0, 0, width, height);

            // Dessiner les connexions réseau
            const maxDist = 130;
            const len = particles.length;

            for (let i = 0; i < len; i++) {
                const p1 = particles[i];
                p1.x += p1.vx;
                p1.y += p1.vy;

                // Rebond bords
                if (p1.x < 0 || p1.x > width) p1.vx *= -1;
                if (p1.y < 0 || p1.y > height) p1.vy *= -1;

                // Réaction souris subtile
                const dxm = p1.x - mouse.x;
                const dym = p1.y - mouse.y;
                const distMouse = Math.sqrt(dxm * dxm + dym * dym);
                if (distMouse < mouse.radius) {
                    const force = (1 - distMouse / mouse.radius) * 1.5;
                    p1.x += (dxm / distMouse) * force;
                    p1.y += (dym / distMouse) * force;
                }

                // Particule point
                ctx.beginPath();
                ctx.arc(p1.x, p1.y, p1.radius, 0, Math.PI * 2);
                ctx.fillStyle = `hsla(${p1.hue}, 90%, 65%, ${p1.baseAlpha})`;
                ctx.shadowColor = `hsl(${p1.hue}, 100%, 60%)`;
                ctx.shadowBlur = 6;
                ctx.fill();

                // Lignes de connexion
                for (let j = i + 1; j < len; j++) {
                    const p2 = particles[j];
                    const dx = p1.x - p2.x;
                    const dy = p1.y - p2.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);

                    if (dist < maxDist) {
                        const alpha = (1 - dist / maxDist) * 0.18;
                        ctx.beginPath();
                        ctx.moveTo(p1.x, p1.y);
                        ctx.lineTo(p2.x, p2.y);
                        ctx.strokeStyle = `rgba(0, 240, 255, ${alpha})`;
                        ctx.lineWidth = 0.8;
                        ctx.shadowBlur = 0;
                        ctx.stroke();
                    }
                }
            }

            animationFrameId = requestAnimationFrame(drawParticles);
        }

        window.addEventListener('resize', resizeCanvas);
        window.addEventListener('mousemove', (e) => {
            mouse.x = e.clientX;
            mouse.y = e.clientY;
        });
        window.addEventListener('mouseleave', () => {
            mouse.x = -9999;
            mouse.y = -9999;
        });

        resizeCanvas();
        if (!prefersReducedMotion) {
            drawParticles();
        }
    }

    // ========================================================================
    // 2. EQUALIZER AUDIO DU COMMENTATEUR KI FRAID
    // ========================================================================
    let equalizerInterval = null;

    function setupCasterVisualizer() {
        const bubble = document.getElementById('casterSpeechBubble');
        if (!bubble || document.getElementById('casterVisualizer')) return;

        const viz = document.createElement('div');
        viz.id = 'casterVisualizer';
        viz.className = 'caster-visualizer';
        viz.innerHTML = `
            <span class="vbar"></span>
            <span class="vbar"></span>
            <span class="vbar"></span>
            <span class="vbar"></span>
            <span class="vbar"></span>
        `;
        bubble.appendChild(viz);
    }

    function setVisualizerActive(active) {
        const viz = document.getElementById('casterVisualizer');
        if (!viz) return;

        if (active) {
            viz.classList.add('speaking');
            if (equalizerInterval) clearInterval(equalizerInterval);
            const bars = viz.querySelectorAll('.vbar');
            equalizerInterval = setInterval(() => {
                bars.forEach(bar => {
                    const h = Math.floor(Math.random() * 18 + 4);
                    bar.style.height = `${h}px`;
                });
            }, 90);
        } else {
            viz.classList.remove('speaking');
            if (equalizerInterval) {
                clearInterval(equalizerInterval);
                equalizerInterval = null;
            }
            const bars = viz.querySelectorAll('.vbar');
            bars.forEach(bar => {
                bar.style.height = '4px';
            });
        }
    }

    // Écouter les événements de voix du commentateur
    document.addEventListener('caster:speak:start', () => setVisualizerActive(true));
    document.addEventListener('caster:speak:end', () => setVisualizerActive(false));

    // ========================================================================
    // 3. ENTRANCE ANIMATIONS (GSAP)
    // ========================================================================
    function runEntranceAnimations() {
        if (typeof gsap === 'undefined') return;

        const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

        // Bandeau IoT
        tl.from('.iot-led-station', {
            y: -25,
            opacity: 0,
            duration: 0.6
        });

        // Header Titre & Logo
        tl.from('.brand-header h1', {
            scale: 0.88,
            opacity: 0,
            duration: 0.7,
            ease: 'back.out(1.7)'
        }, '-=0.3');

        tl.from('.brand-header .subtitle', {
            opacity: 0,
            y: 8,
            duration: 0.4
        }, '-=0.4');

        // Caster HUD Card
        tl.from('.caster-hud-card', {
            y: 18,
            opacity: 0,
            duration: 0.5
        }, '-=0.2');

        // Boîtes d'action du Lobby
        tl.from('.lobby-card', {
            opacity: 0,
            y: 20,
            duration: 0.6
        }, '-=0.3');

        tl.from('.actions-grid > .action-box', {
            opacity: 0,
            y: 25,
            stagger: 0.12,
            duration: 0.5,
            ease: 'power2.out'
        }, '-=0.4');
    }

    // ========================================================================
    // 4. JUICE VISUEL EN JEU (Impacts, Numpad, Combos)
    // ========================================================================
    window.ArenaAnimations = {
        pulseCell(cellEl, isSuccess = true) {
            if (!cellEl) return;
            if (typeof gsap !== 'undefined') {
                gsap.fromTo(cellEl, 
                    { scale: 0.82, backgroundColor: isSuccess ? 'rgba(0, 240, 255, 0.4)' : 'rgba(239, 68, 68, 0.4)' },
                    { scale: 1, backgroundColor: '', duration: 0.35, ease: 'elastic.out(1.2, 0.4)' }
                );
            } else {
                cellEl.classList.add(isSuccess ? 'cell-pop' : 'cell-shake');
                setTimeout(() => cellEl.classList.remove('cell-pop', 'cell-shake'), 400);
            }
        },

        triggerComboBurst(comboCount = 2) {
            const arena = document.querySelector('.arena-container');
            if (arena) {
                arena.classList.add('combo-flash');
                setTimeout(() => arena.classList.remove('combo-flash'), 600);
            }
        },

        shakeBoard() {
            const board = document.querySelector('.sudoku-board-container');
            if (!board) return;
            if (typeof gsap !== 'undefined') {
                gsap.to(board, {
                    x: () => (Math.random() - 0.5) * 12,
                    duration: 0.05,
                    repeat: 5,
                    yoyo: true,
                    onComplete: () => gsap.set(board, { x: 0 })
                });
            }
        },

        celebrateVictory() {
            if (typeof gsap === 'undefined') return;
            const modal = document.querySelector('#gameOverModal .modal-card');
            if (modal) {
                gsap.fromTo(modal,
                    { scale: 0.7, opacity: 0, rotationY: 20 },
                    { scale: 1, opacity: 1, rotationY: 0, duration: 0.6, ease: 'back.out(1.5)' }
                );
            }
        }
    };

    // ========================================================================
    // 5. BOUTON TOGGLE VOIX DU CASTER
    // ========================================================================
    function setupVoiceToggle() {
        const btnToggleVoice = document.getElementById('btnToggleVoice');
        const voiceIcon = document.getElementById('voiceIcon');

        if (btnToggleVoice && window.caster) {
            const updateIcon = (enabled) => {
                if (voiceIcon) voiceIcon.textContent = enabled ? '🔊' : '🔇';
                btnToggleVoice.title = enabled 
                    ? 'Couper la voix du Caster' 
                    : 'Activer la voix du Caster';
                btnToggleVoice.classList.toggle('muted', !enabled);
            };

            updateIcon(window.caster.isVoiceEnabled);

            btnToggleVoice.addEventListener('click', () => {
                const isEnabled = window.caster.toggleVoice();
                updateIcon(isEnabled);
                if (window.showToast) {
                    window.showToast(
                        isEnabled ? '🎙️ Voix KI FRAID activée !' : '🔇 Voix KI FRAID coupée.',
                        'info',
                        2500
                    );
                }
            });
        }
    }

    // ========================================================================
    // 6. INITIALISATION AU CHARGEMENT DU DOM
    // ========================================================================
    document.addEventListener('DOMContentLoaded', () => {
        setupCasterVisualizer();
        setupVoiceToggle();
        runEntranceAnimations();
    });

})();
