# vision_match.py
import os
import cv2
import mss
import numpy as np
import win32gui

# Ten moduł zakłada, że host_api.py ma już:
# - find_window_by_title_substring(title) -> (hwnd, err)
# Dlatego wstrzykujemy go jako callback.

def grab_roi_bgr(find_window_by_title_substring, title: str, rect: dict, pad: int = 0):
    """
    Screenshot ROI relatywnie do okna.

    Zwraca: (roi_bgr, meta)
    meta:
      hwnd, abs_x_p, abs_y_p, w_p, h_p, win_left, win_top,
      rect_input, rect_used, pad
    """
    title = (title or "").strip()
    if not title:
        raise ValueError("Missing title")

    # rect walidacja
    x = int(rect["x"]); y = int(rect["y"]); w = int(rect["w"]); h = int(rect["h"])
    if w <= 0 or h <= 0:
        raise ValueError("Invalid rect size")

    hwnd, err = find_window_by_title_substring(title)
    if err:
        raise RuntimeError(err)

    left, top, _, _ = win32gui.GetWindowRect(hwnd)

    abs_x = left + x
    abs_y = top + y

    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    with mss.mss() as sct:
        monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}
        img = np.array(sct.grab(monitor))  # BGRA

    roi_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    meta = dict(
        hwnd=int(hwnd),
        abs_x_p=int(abs_x_p), abs_y_p=int(abs_y_p),
        w_p=int(w_p), h_p=int(h_p),
        win_left=int(left), win_top=int(top),
        rect_input={"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
        rect_used={"x": int(abs_x_p), "y": int(abs_y_p), "w": int(w_p), "h": int(h_p)},
        pad=int(pad),
    )
    return roi_bgr, meta


def _load_template_bgr_and_mask(path: str):
    tpl = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if tpl is None:
        raise RuntimeError(f"Template not found: {path}")

    # grayscale
    if tpl.ndim == 2:
        tpl_bgr = cv2.cvtColor(tpl, cv2.COLOR_GRAY2BGR)
        return tpl_bgr, None

    # BGRA with alpha as mask
    if tpl.shape[2] == 4:
        tpl_bgr = tpl[:, :, :3]
        alpha = tpl[:, :, 3]
        mask = cv2.threshold(alpha, 0, 255, cv2.THRESH_BINARY)[1]
        return tpl_bgr, mask

    # BGR
    return tpl[:, :, :3], None


def find_template_points(
    roi_bgr: "np.ndarray",
    template_path: str,
    thr: float = 0.88,
    max_results: int = 50,
    nms_radius: int = 10,
):
    """
    Multi-hit template matching.
    Zwraca:
      hits: [{score, x,y,w,h,cx,cy}]  (koordy w ROI)
      debug: {tpl_w, tpl_h, max_score}
    """
    tpl_bgr, mask = _load_template_bgr_and_mask(template_path)
    th, tw = tpl_bgr.shape[:2]

    # Alpha-mask -> TM_CCORR_NORMED
    if mask is not None:
        res = cv2.matchTemplate(roi_bgr, tpl_bgr, cv2.TM_CCORR_NORMED, mask=mask)
    else:
        res = cv2.matchTemplate(roi_bgr, tpl_bgr, cv2.TM_CCOEFF_NORMED)

    if res.size == 0:
        return [], {"tpl_w": int(tw), "tpl_h": int(th), "max_score": 0.0}

    max_score = float(res.max())

    ys, xs = np.where(res >= float(thr))
    if len(xs) == 0:
        return [], {"tpl_w": int(tw), "tpl_h": int(th), "max_score": max_score}

    scores = res[ys, xs]
    order = np.argsort(scores)[::-1]

    hits = []
    taken = []

    for idx in order:
        x = int(xs[idx]); y = int(ys[idx])
        score = float(scores[idx])

        # proste NMS (tłumienie duplikatów blisko siebie)
        ok = True
        for (tx, ty) in taken:
            if abs(x - tx) <= nms_radius and abs(y - ty) <= nms_radius:
                ok = False
                break
        if not ok:
            continue

        taken.append((x, y))
        hits.append({
            "score": score,
            "x": x, "y": y,
            "w": int(tw), "h": int(th),
            "cx": int(x + tw // 2),
            "cy": int(y + th // 2),
        })

        if len(hits) >= int(max_results):
            break

    debug = {"tpl_w": int(tw), "tpl_h": int(th), "max_score": max_score}
    return hits, debug


def find_templates_in_window_roi(
    find_window_by_title_substring,
    base_dir: str,
    temp_dir: str,
    title: str,
    rect: dict,
    templates: list,
    thr: float = 0.88,
    pad: int = 0,
    max_results: int = 30,
    nms_radius: int = 10,
    debug_save: bool = False,
    templates_dir_name: str = "search_templates",
):
    """
    Orkiestracja: grab ROI + match wielu template + mapowanie na koordy relatywne do okna.
    Zwraca dict gotowy do jsonify.
    """
    templates_dir = os.path.join(base_dir, templates_dir_name)
    os.makedirs(templates_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    roi_bgr, meta = grab_roi_bgr(find_window_by_title_substring, title=title, rect=rect, pad=pad)

    if debug_save:
        cv2.imwrite(os.path.join(temp_dir, "find_roi_raw.png"), roi_bgr)

    roi_origin_rel_x = meta["abs_x_p"] - meta["win_left"]
    roi_origin_rel_y = meta["abs_y_p"] - meta["win_top"]

    out = []
    for tname in templates:
        safe = os.path.basename(str(tname))
        tpath = os.path.join(templates_dir, safe)

        hits, dbg = find_template_points(
            roi_bgr=roi_bgr,
            template_path=tpath,
            thr=thr,
            max_results=max_results,
            nms_radius=nms_radius,
        )

        mapped = []
        for h in hits:
            mapped.append({
                "score": h["score"],
                "roi": {"x": h["x"], "y": h["y"], "cx": h["cx"], "cy": h["cy"], "w": h["w"], "h": h["h"]},
                "window": {
                    "x": int(roi_origin_rel_x + h["x"]),
                    "y": int(roi_origin_rel_y + h["y"]),
                    "cx": int(roi_origin_rel_x + h["cx"]),
                    "cy": int(roi_origin_rel_y + h["cy"]),
                },
            })

        out.append({
            "template": safe,
            "count": len(mapped),
            "hits": mapped,
            "debug": dbg,
        })

    resp = dict(ok=True, matches=out, **meta)
    return resp
