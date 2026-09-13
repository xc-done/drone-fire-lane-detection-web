# Drone-Assisted Fire Lane Occupancy Detection System

> A computer vision project that uses drone inspection footage to identify potential obstructions in emergency access routes and turn them into reviewable visual evidence.

**Project by:** `[Student name]`  
**School:** `[School name]`  
**Project year:** `[Year]`

> **About this page:** This README is a project showcase, not a software installation guide. Replace every bracketed placeholder with real project information or media before sharing this repository.

---

## The Problem

Fire lanes are essential for emergency response, but they can be blocked by vehicles or other objects. Manual inspection is time-consuming, especially when inspectors need to review long videos or cover a large area. Fixed cameras may also provide limited coverage or inflexible viewpoints.

This project explores whether drone footage and computer vision can support a faster first-pass inspection workflow while keeping a human reviewer in the loop.

### Why use a drone?

An aerial platform can capture wider areas and more flexible viewpoints than a single fixed camera. In this project, the drone is the data-collection layer: it records inspection footage that can later be analyzed by the detection model.

---

## The Project

I built a prototype that connects four steps into one inspection workflow:

1. **Capture:** collect fire-lane footage with a drone.
2. **Detect:** analyze images or video frames with a YOLO-based object detection model.
3. **Review:** display annotated results and detection information in a web interface.
4. **Report:** preserve key frames and detection information for later review.

```text
Drone inspection footage
          ↓
   Computer vision detection
          ↓
       Web-based review
          ↓
     Inspection evidence
```

---

## Project Showcase

### 1. Drone Inspection Input

**[PLACE PHOTO HERE: Original drone inspection footage]**

Add one clear still image from the original drone video. It should show the inspection viewpoint and make it obvious that the footage was collected from an aerial or elevated perspective.

**Suggested caption:**  
`Original aerial footage collected during a fire-lane inspection.`

**Optional second image:**  
`A wider view showing the area covered by the drone.`

### 2. Detection Output

**[PLACE PHOTO HERE: Annotated detection result]**

Add a frame from the same scene after model inference. The bounding boxes and labels should be large enough to read in a GitHub preview.

**Suggested caption:**  
`The detection model highlights objects identified in the inspection frame.`

### 3. Web Application

**[PLACE SCREENSHOT HERE: Detection web interface]**

Add a screenshot of the working web application. The screenshot should show the shared detection display area and, if possible, the uploaded video or annotated result on screen.

**Suggested caption:**  
`A web interface for uploading inspection media and reviewing detection results.`

### 4. Generated Report

**[PLACE SCREENSHOT HERE: Generated HTML inspection report]**

Add a screenshot of the generated report showing key frames, timestamps, or detection summaries.

**Suggested caption:**  
`Key frames and detection information organized into an inspection report.`

---

## Project Demo Video

**[PLACE VIDEO LINK HERE: English demo video, approximately 2 minutes and no longer than 3 minutes]**

The video should be short and visual. It should not be a full lecture or a slide-by-slide reading. Show the product working from input to output.

### Recommended video sequence

**0:00-0:15 — The problem**  
Show the fire-lane context or an original drone frame. Briefly explain why manual inspection is difficult.

**0:15-0:35 — The idea**  
Show the project title and the workflow: drone footage → detection model → web review → report.

**0:35-1:20 — The prototype**  
Show the web application, upload an inspection video, start detection, and show annotated frames appearing in the shared display area.

**1:20-1:45 — The output**  
Show the detection logs and open the generated HTML report with key frames and timestamps.

**1:45-2:10 — Results and limitations**  
Show one or two representative results, then explain that performance can change with lighting, altitude, viewpoint, and background.

**2:10-2:25 — Closing**  
State what the prototype demonstrates and what you plan to improve next.

### Suggested video opening

> Fire lanes are critical for emergency response, but they can be blocked by vehicles or other objects. I built a drone-assisted computer vision system to help turn inspection footage into reviewable detection evidence.

### Suggested video closing

> This prototype connects drone inspection, computer vision, and web-based reporting in one workflow. My next step is to collect more diverse drone footage and improve its performance in unfamiliar environments.

---

## How It Works

### Capture

The drone records inspection footage from an elevated and flexible viewpoint. The footage serves as the input to the rest of the system.

### Detect

The trained YOLO model analyzes an image or processes a video frame by frame. It returns detected objects, locations, class labels, and confidence scores.

### Review

The web application displays the annotated image or video and provides detection logs. Images and videos are presented through a shared result area so the user can review both types of input in one place.

### Report

After video processing, the system organizes selected key frames and detection information into an HTML inspection report. The report makes the results easier to save, review, and discuss.

---

## Results

The prototype demonstrates that drone footage can be connected to a YOLO detection workflow and presented through a usable web interface. It can:

- process uploaded images and inspection videos;
- display visual detection results with bounding boxes;
- show detection information during video processing;
- preserve selected key frames and report information.

**[PLACE VERIFIED RESULT HERE]**  
Add one result that you have actually measured or observed clearly. For example: a test-set metric, the number of processed videos, or a specific behavior observed during evaluation. Do not add an accuracy claim unless it can be supported by your evaluation records.

---

## My Contribution

**[REPLACE THIS SECTION WITH THE STUDENT'S ACTUAL CONTRIBUTION]**

Use specific, truthful statements such as:

- I organized and prepared the detection data.
- I trained and tested the YOLO detection model.
- I participated in planning or collecting drone-based inspection footage.
- I built the image and video detection workflow.
- I connected the model to the web interface.
- I designed the result display and report generation process.
- I evaluated the prototype on scenes outside the original training examples.

If a part was completed as a team, describe it as a team contribution rather than claiming it as an individual task.

---

## Limitations and Next Steps

The current prototype performs best on scenes similar to its training data. Changes in lighting, flight altitude, camera angle, distance, background, and object appearance can affect detection quality. The system is designed to support human review, not to replace professional inspection or make final enforcement decisions.

Next steps include:

- collecting more diverse drone inspection footage;
- improving generalization to new locations and viewpoints;
- adding object tracking to reduce repeated counting in videos;
- exploring live drone video input;
- improving report summaries and alert functions.

---

## Technology

- **Drone footage:** inspection input
- **YOLO:** object detection
- **OpenCV:** video frame processing
- **Flask:** web application backend
- **HTML, CSS, and JavaScript:** browser interface
- **HTML report generation:** inspection record output

The technical stack supports the application, but the central idea is the workflow: **drone collection → AI detection → web review → inspection evidence**.

---

## Contact and Links

**Student:** `[Student name]`  
**School:** `[School name]`  
**Email:** `[Optional public contact]`  
**Project showcase:** `[Add public project page URL]`  
**Demo video:** `[Add public video URL]`  
**Working prototype:** `[Add public prototype URL, if available]`

---

## Media Checklist Before Sharing

- [ ] Replace the student, school, and year placeholders.
- [ ] Add one original drone inspection photo.
- [ ] Add one annotated detection result from the same or a comparable scene.
- [ ] Add one screenshot of the working web interface.
- [ ] Add one screenshot of the generated report.
- [ ] Add the English demo video link.
- [ ] Keep the demo video between 2 and 3 minutes.
- [ ] Add one verified result without exaggerating performance.
- [ ] Rewrite the contribution section according to the student's real work.
- [ ] Check that every public link opens without login, download, or extra setup.
