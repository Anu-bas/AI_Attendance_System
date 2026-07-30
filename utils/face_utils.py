"""
Core AI logic: face detection, encoding, and matching.

Pipeline:
 1. encode_student_face()  -> run once when a student profile photo is uploaded.
 2. recognize_faces_in_image() -> run on every classroom/group photo upload.
"""
import json
import cv2
import numpy as np
import face_recognition

from config import Config


class FaceProcessingError(Exception):
    """Raised for any image that can't be used (no face, too blurry, etc.)."""
    pass


def _load_rgb_image(path):
    image = cv2.imread(path)
    if image is None:
        raise FaceProcessingError(f"Could not read image file: {path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def encode_student_face(image_path):
    """
    Detect the (single) face in a student's profile photo and return its
    128-d encoding as a JSON string ready for DB storage.
    Raises FaceProcessingError if zero or multiple faces are found.
    """
    rgb = _load_rgb_image(image_path)
    locations = face_recognition.face_locations(rgb, model="hog")

    if len(locations) == 0:
        raise FaceProcessingError(
            "No face detected in the uploaded photo. Please upload a clear, "
            "front-facing passport-size photo with good lighting."
        )
    if len(locations) > 1:
        raise FaceProcessingError(
            "Multiple faces detected in the profile photo. Please upload a photo "
            "containing only the student's face."
        )

    encodings = face_recognition.face_encodings(rgb, known_face_locations=locations)
    encoding = encodings[0]
    return json.dumps(encoding.tolist())


def decode_encoding(json_str):
    return np.array(json.loads(json_str))


def recognize_faces_in_image(image_path, known_encodings, known_ids, known_names,
                              tolerance=None):
    """
    Detect all faces in a classroom photo and match each against the known
    student encodings.

    Args:
        image_path: path to the uploaded group photo
        known_encodings: list[np.ndarray] of student face encodings
        known_ids: list[int] student DB ids, same order as known_encodings
        known_names: list[str] student names, same order as known_encodings
        tolerance: float, lower = stricter. Defaults to Config.FACE_MATCH_TOLERANCE

    Returns:
        dict with:
            'total_faces': int, number of faces detected in the photo
            'matches': list of dicts:
                {student_id, name, confidence (0-100), box: (top,right,bottom,left)}
            'unmatched_boxes': list of face boxes that couldn't be matched to anyone
    """
    if tolerance is None:
        tolerance = Config.FACE_MATCH_TOLERANCE

    rgb = _load_rgb_image(image_path)
    face_locations = face_recognition.face_locations(rgb, model="hog")

    if len(face_locations) == 0:
        raise FaceProcessingError(
            "No faces were detected in the classroom photo. Please upload a "
            "clearer, well-lit image."
        )

    face_encodings = face_recognition.face_encodings(rgb, known_face_locations=face_locations)

    matches = []
    unmatched_boxes = []
    matched_student_ids = set()

    known_encodings_arr = np.array(known_encodings) if known_encodings else np.empty((0, 128))

    for box, face_encoding in zip(face_locations, face_encodings):
        if len(known_encodings_arr) == 0:
            unmatched_boxes.append(box)
            continue

        distances = face_recognition.face_distance(known_encodings_arr, face_encoding)
        best_idx = int(np.argmin(distances))
        best_distance = float(distances[best_idx])

        if best_distance <= tolerance:
            student_id = known_ids[best_idx]
            # Avoid double-matching the same student to two faces in one photo
            if student_id in matched_student_ids:
                unmatched_boxes.append(box)
                continue
            confidence = round(max(0.0, (1 - best_distance)) * 100, 2)
            matches.append({
                "student_id": student_id,
                "name": known_names[best_idx],
                "confidence": confidence,
                "box": box,
            })
            matched_student_ids.add(student_id)
        else:
            unmatched_boxes.append(box)

    return {
        "total_faces": len(face_locations),
        "matches": matches,
        "unmatched_boxes": unmatched_boxes,
    }


def draw_annotated_image(image_path, matches, unmatched_boxes, output_path):
    """Draw bounding boxes + names/confidence on the classroom photo for display."""
    image = cv2.imread(image_path)

    for m in matches:
        top, right, bottom, left = m["box"]
        cv2.rectangle(image, (left, top), (right, bottom), (172, 92, 246), 2)  # violet
        label = f"{m['name']} ({m['confidence']}%)"
        cv2.rectangle(image, (left, bottom - 22), (right, bottom), (172, 92, 246), cv2.FILLED)
        cv2.putText(image, label, (left + 4, bottom - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    for box in unmatched_boxes:
        top, right, bottom, left = box
        cv2.rectangle(image, (left, top), (right, bottom), (0, 0, 255), 2)  # red = unknown
        cv2.putText(image, "Unknown", (left + 4, bottom - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    cv2.imwrite(output_path, image)
    return output_path
