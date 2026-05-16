// Creator Page Logic
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('generateForm');
    const previewEmpty = document.getElementById('preview-empty-state');
    const previewText = document.getElementById('preview-text');
    const previewImage = document.getElementById('preview-image');
    const actionButtons = document.getElementById('post-actions');
    const generateBtn = form.querySelector('button[type="submit"]');

    let currentPostData = null;
    
    // Sync Preview with Active Account
    async function syncPreviewAccount() {
        try {
            const user = await API.getCurrentUser();
            if (user && user.active_account) {
                const acc = user.active_account;
                const nameEl = document.getElementById('preview-name');
                const avatarEl = document.getElementById('preview-avatar');
                const headlineEl = document.getElementById('preview-headline');
                
                if (nameEl) nameEl.textContent = acc.name;
                if (avatarEl) avatarEl.src = acc.profile_picture_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(acc.name)}&background=0a66c2&color=fff`;
                
                if (headlineEl) {
                    if (acc.linkedin_id && acc.linkedin_id.includes(':organization:')) {
                        headlineEl.textContent = 'Company Page';
                    } else {
                        headlineEl.textContent = 'AI & Machine Learning Enthusiast';
                    }
                }
            }
        } catch (e) {
            console.error('Failed to sync preview account:', e);
        }
    }
    
    syncPreviewAccount();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const topic = document.getElementById('topic').value.trim();
        if(!topic) {
            showToast('Please enter a topic', 'error');
            return;
        }

        // Setup loading state
        const originalBtnHTML = generateBtn.innerHTML;
        generateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';
        generateBtn.disabled = true;

        try {
            const tone = document.getElementById('tone').value;
            const length = document.getElementById('length').value;
            const imageStyle = document.getElementById('imageStyle').value;

            const result = await API.generateContent(topic, tone, length, imageStyle);

            if (!result || !result.text) {
                throw new Error('No content returned from AI. Please try again.');
            }

            // Update preview text
            previewText.textContent = result.text;

            // Update preview image
            const imageWrap = document.getElementById('preview-image-wrap');
            if (result.image_url) {
                previewImage.src = result.image_url;
                previewImage.onerror = () => { if (imageWrap) imageWrap.style.display = 'none'; };
                previewImage.onload = () => { if (imageWrap) imageWrap.style.display = ''; };
                if (imageWrap) imageWrap.style.display = '';
            } else {
                if (imageWrap) imageWrap.style.display = 'none';
            }

            // Show the preview and action buttons
            previewEmpty.classList.add('hidden');
            actionButtons.classList.remove('hidden');

            // Store current data for posting
            currentPostData = {
                topic: topic,
                generated_text: result.text,
                generated_image_url: result.image_url || null,
                tone: tone,
                length: length,
                image_style: imageStyle
            };

            showToast('Content generated successfully!');
            
        } catch (error) {
            console.error(error);
            showToast(error.message || 'Failed to generate content', 'error');
        } finally {
            generateBtn.innerHTML = originalBtnHTML;
            generateBtn.disabled = false;
        }
    });

    // Handle Post Now
    const postNowBtn = actionButtons.querySelector('button:last-child');
    postNowBtn.addEventListener('click', async () => {
        if (!currentPostData) return;

        const originalBtnHTML = postNowBtn.innerHTML;
        postNowBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Posting...';
        postNowBtn.disabled = true;

        try {
            // 1. Create the post in DB
            const postResponse = await API.createPost({
                ...currentPostData,
                status: 'Draft'
            });

            // 2. Publish it
            await API.publishPost(postResponse.post_id);

            showToast('Post published successfully to LinkedIn!');
            
            // Redirect to dashboard after a short delay
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 2000);

        } catch (error) {
            console.error(error);
            showToast(error.message || 'Failed to post to LinkedIn', 'error');
        } finally {
            postNowBtn.innerHTML = originalBtnHTML;
            postNowBtn.disabled = false;
        }
    });

    // Handle Schedule
    const scheduleBtn = actionButtons.querySelector('button:first-child');
    scheduleBtn.addEventListener('click', async () => {
        if (!currentPostData) return;
        
        // Better UX: Ask for date and time separately to make it clear
        const dateInput = prompt("Enter Date (YYYY-MM-DD):", new Date().toISOString().split('T')[0]);
        if (!dateInput) return;
        
        const timeInput = prompt("Enter Time (e.g., 04:30 PM):", "09:00 AM");
        if (!timeInput) return;

        try {
            // Convert 12h to 24h for the Date object
            const [time, modifier] = timeInput.split(' ');
            let [hours, minutes] = time.split(':');
            if (hours === '12') hours = '00';
            if (modifier.toUpperCase() === 'PM') hours = parseInt(hours, 10) + 12;
            
            const scheduledDate = new Date(`${dateInput}T${hours}:${minutes}:00`);
            const scheduledTimeUTC = scheduledDate.toISOString();
            
            await API.createPost({
                ...currentPostData, // This contains the FULL generated_text
                status: 'Scheduled',
                scheduled_time: scheduledTimeUTC
            });

            showToast('Post scheduled successfully with full content!');
            window.location.href = '/calendar';

        } catch (error) {
            console.error('Scheduling Error:', error);
            showToast('Invalid format. Use YYYY-MM-DD and HH:MM AM/PM', 'error');
        }
    });
});
