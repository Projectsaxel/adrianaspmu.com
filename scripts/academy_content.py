"""HTML body for academy / training hub (from adrianaspmu.com/training/)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACADEMY_IMG = ROOT / "assets" / "images" / "academy"


def _imgs(subdir: str) -> list[str]:
    p = ACADEMY_IMG / subdir
    if not p.is_dir():
        return []
    return sorted(f.name for f in p.glob("*.jpg"))


def academy_body(img, depth: int = 1, course_href_base: str = "") -> str:
    gallery = _imgs("gallery")
    gallery_imgs = "".join(
        img(f"academy/gallery/{name}", f"Adriana's PMU Academy — class photo {i + 1}", depth, "gallery-marquee-img")
        for i, name in enumerate(gallery)
    )
    gallery_track = gallery_imgs + gallery_imgs

    slides = _imgs("slides")
    slide_cards = "".join(
        f'<figure class="academy-slide-card">{img(f"academy/slides/{name}", "PMU training slide", depth, "academy-slide-img")}</figure>'
        for name in slides
    )

    students = _imgs("students")
    student_avatars = "".join(
        img(f"academy/students/{name}", "PMU academy student", depth, "student-avatar")
        for name in students
    )

    return f"""
<section class="academy-hero">
  <div class="academy-hero-media" aria-hidden="true">
    {img("academy/hero.webp", "", depth, "academy-hero-bg")}
    <div class="academy-hero-overlay"></div>
  </div>
  <div class="container academy-hero-content">
    <p class="section-label section-label--light">Adriana's Academy</p>
    <h1>Learn the Art of Permanent Makeup</h1>
    <p class="direct-answer">At <strong>Adriana's Academy</strong>, we teach more than techniques — we shape <strong>confident, skilled artists ready</strong> to build successful careers in the PMU industry. Created by <strong>Adriana Santos</strong>, an experienced artist and educator recognized for excellence and innovation.</p>
    <a class="btn btn-primary academy-video-cta" href="https://www.youtube.com/watch?v=qmjz3Xohiro" target="_blank" rel="noopener noreferrer">Watch academy video</a>
  </div>
</section>

<section class="trust-bar academy-stats" aria-label="Academy credentials">
  <div class="container trust-bar-inner">
    <div><span class="stat-number">20+</span><span class="stat-label">Years of experience</span></div>
    <div><span class="stat-number">300+</span><span class="stat-label">Students trained</span></div>
    <div><span class="stat-number">5,000+</span><span class="stat-label">Happy clients</span></div>
  </div>
</section>

<section class="section section--elegant">
  <div class="container heading-centered">
    <h2>Grow, Learn, and Succeed with Adriana's Academy</h2>
    <p class="direct-answer">Step into a world of growth and opportunity with our <strong>classes</strong> — where hands-on learning meets artistry and confidence.</p>
  </div>
  <div class="container academy-video-embed">
    <a class="academy-video-poster" href="https://www.youtube.com/watch?v=qmjz3Xohiro" target="_blank" rel="noopener noreferrer" aria-label="Play academy introduction video on YouTube">
      {img("academy/hero.webp", "Adriana's PMU Academy introduction video", depth, "academy-video-poster-img")}
      <span class="academy-video-play" aria-hidden="true">▶</span>
    </a>
  </div>
</section>

<section class="section section-alt">
  <div class="container">
    <p class="section-label section-label--center">Instructor</p>
    <h2 class="heading-centered">Meet Our Instructor</h2>
    <p class="direct-answer heading-centered">With over 18 years of experience, <strong>Adriana Santos</strong> has transformed the beauty industry through her artistry and education. Known for her precision, compassion, and dedication to excellence, she has trained hundreds of students and helped women worldwide build confidence, independence, and successful PMU careers.</p>
    <div class="hero-grid academy-instructor-grid">
      <div class="hero-visual">
        {img("academy/adriana.jpg", "Adriana Santos — PMU educator", depth, "service-hero-img")}
      </div>
      <div>
        <h3>Adriana Santos</h3>
        <p>Adriana is a <strong>Brazilian permanent makeup artist and educator</strong> with over 18 years of experience in the beauty industry. She has built a solid reputation for her professionalism, attention to detail, and passion for teaching.</p>
        <p>As the founder of <strong>Adriana's Academy</strong>, she has trained <strong>over 300 students</strong> through hands-on, high-quality programs designed to build real confidence and skill. With more than <strong>5,000 procedures performed</strong>, Adriana continues to shape the next generation of PMU artists with her modern approach and commitment to excellence.</p>
        <a class="btn btn-secondary" href="https://www.instagram.com/adrianas_pmu/" target="_blank" rel="noopener noreferrer">Academy Instagram</a>
      </div>
    </div>
  </div>
</section>

<section class="section section--elegant">
  <div class="container">
    <h2 class="heading-centered">Permanent Makeup Classes</h2>
    <div class="academy-students-row">
      <div class="student-avatars" aria-hidden="true">{student_avatars}</div>
      <p class="academy-students-label"><strong>More than 300 students trained</strong></p>
    </div>
    <p class="direct-answer heading-centered">Join a <strong>transformative experience</strong> that builds confidence and mastery. Through hands-on training, expert guidance, and real models, you'll gain the knowledge and technique to <strong>grow your talent and transform your future in permanent makeup</strong>.</p>
  </div>
  <div class="gallery-marquee" aria-hidden="true">
    <div class="gallery-marquee-track">{gallery_track}</div>
  </div>
</section>

<section class="section section-alt">
  <div class="container feature-grid">
    <article class="feature-card">
      <h3>In-Person Experience</h3>
      <p>Our in-person classes are designed for <strong>direct interaction, hands-on practice, and continuous mentorship</strong>, ensuring every student gains real experience and confidence in every technique. Students are also <strong>welcome to retake classes anytime</strong> to refresh their knowledge and strengthen their skills.</p>
    </article>
    <article class="feature-card">
      <h3>Hands-on Model</h3>
      <p>Each course includes <strong>live model sessions for every technique</strong>, allowing students to apply what they learn under professional guidance and achieve real, visible results that build confidence and precision.</p>
    </article>
    <article class="feature-card">
      <h3>Elegant &amp; Fully Equipped</h3>
      <p>Train in a <strong>spacious, elegant, and well-structured environment</strong> designed to inspire focus and creativity. Our academy offers the perfect setting for growth — beautifully organized, welcoming, and equipped with everything you need to learn, practice, and succeed.</p>
    </article>
  </div>
</section>

<section class="section section--elegant">
  <div class="container hero-grid">
    <div>
      <h2>Personalized Attention, Real Results</h2>
      <p>Our intensive in-person courses are conducted in intimate group settings, <strong>limited to a small number of participants</strong> to ensure personalized attention.</p>
      <p>Most classes include <strong>practical sessions with hands-on models</strong>, offering real-world experience, complemented by support to enhance your skills, achieve your goals, and advance your professional journey.</p>
    </div>
    <div class="hero-visual">
      {img("academy/in-person-class.jpg", "In-person PMU class at Adriana's Academy", depth, "service-hero-img")}
    </div>
  </div>
</section>

<section class="section section-alt">
  <div class="container">
    <article class="course-split card">
      <div class="hero-visual">
        {img("academy/pmu-100h.jpg", "100-Hour Fundamental PMU training", depth, "service-hero-img")}
      </div>
      <div>
        <span class="badge">9-Day Course</span>
        <h2>100 Hours Fundamental</h2>
        <p>If you're looking for the perfect course to start your career in permanent makeup, this is it. Our <strong>100-Hour Fundamental Training</strong>, certified by the <strong>American Academy of Micropigmentation (AAM)</strong>, provides everything you need to become a confident and skilled artist.</p>
        <p>In this <strong>9-day hands-on program</strong>, you'll learn <strong>five essential techniques</strong> — Microblading, Ombre Shading, Microshading, Lip Blush, and Dark Lip Neutralization — while practicing on live models under expert guidance.</p>
        <p class="price">$7,000</p>
        <a class="btn btn-primary" href="{course_href_base}pmu-100h-fundamental.html">Learn More</a>
      </div>
    </article>
    <article class="course-split card course-split--reverse">
      <div class="hero-visual">
        {img("academy/apprenticeship.jpg", "PMU apprenticeship program", depth, "service-hero-img")}
      </div>
      <div>
        <span class="badge">1-Year Duration</span>
        <h2>Apprenticeship Program</h2>
        <p><strong>Take your PMU training</strong> to the next level with our one-year (or accelerated) <strong>apprenticeship</strong>. Designed to give you real experience, this program includes <strong>advanced model practice, client simulation, marketing, and business training</strong> — preparing you to build confidence, attract clients, and grow a successful career in <strong>permanent makeup</strong>.</p>
        <p class="price">$700/month</p>
        <a class="btn btn-primary" href="{course_href_base}pmu-apprenticeship.html">Learn More</a>
      </div>
    </article>
  </div>
</section>

<section class="section section--elegant section--flush">
  <div class="container">
    <h2 class="heading-centered">Academy Gallery</h2>
    <div class="academy-slides-track" tabindex="0">{slide_cards}</div>
  </div>
</section>

<section class="section section-alt" id="student-reviews">
  <div class="container">
    <p class="section-label section-label--center">Student testimonials</p>
    <h2 class="heading-centered">What Our Students Are Saying</h2>
    <p class="direct-answer heading-centered"><strong>Real experiences</strong>. Lasting impact. Discover how our <strong>training</strong> has empowered students, elevated their skills, and transformed their careers in <strong>permanent makeup</strong>.</p>
    <div class="reviews-trustindex">
      <script defer async src="https://cdn.trustindex.io/loader-feed.js?d0320e757fe86018d9160cf5126"></script>
    </div>
  </div>
</section>

<section class="section section--elegant">
  <div class="container hero-grid academy-location">
    <div class="hero-visual">
      {img("academy/classroom.jpg", "Adriana's Academy classroom in Peabody MA", depth, "service-hero-img")}
    </div>
    <div>
      <h2>Academy Location</h2>
      <h3>Massachusetts, MA</h3>
      <p>Adriana's Academy, located in Peabody, Massachusetts, operates under Adriana Beauty Services, Inc. as the educational division of our permanent makeup clinics.</p>
      <p><strong>39 Cross Street, Suite 206, Peabody, MA 01960</strong><br>
      <a href="tel:+17818538063">(781) 853-8063</a></p>
      <p><strong>Adriana's Academy</strong> was designed to provide a comfortable and inspiring environment for every student. Our space is modern, fully equipped, and carefully prepared to ensure the best learning experience in every technique.</p>
      <a class="btn btn-secondary" href="https://www.instagram.com/adrianasacademy" target="_blank" rel="noopener noreferrer">Adriana's Academy on Instagram</a>
    </div>
  </div>
</section>

<section class="section section-alt section--elegant aam-cert">
  <div class="container hero-grid">
    <div class="hero-visual aam-cert-seal">
      {img("academy/aam-seal.png", "American Academy of Micropigmentation Diamond Certified Trainer", depth, "aam-seal-img")}
    </div>
    <div>
      <h2>Excellence Certification: Diamond Membership</h2>
      <p>Adriana's Permanent Makeup is officially <strong>certified by the American Academy of Micropigmentation (AAM)</strong> with the prestigious <strong>Diamond Certified Trainer</strong> status — the highest level of recognition for instructors.</p>
      <p>This means we follow the strictest standards in quality, ethics, and safety — training professionals who are highly skilled and internationally recognized.</p>
    </div>
  </div>
</section>

<section class="section section--cta">
  <div class="container cta-panel">
    <h2>Ready to Start Your PMU Career?</h2>
    <p>Apply for the 100-Hour Fundamental course or Apprenticeship program today.</p>
    <a class="btn btn-primary" href="../contact.html">Contact the Academy</a>
  </div>
</section>
"""
