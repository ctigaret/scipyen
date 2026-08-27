// Source - https://stackoverflow.com/a/79220216
// Posted by MadRunner, modified by community. See post 'Timeline' for change history
// Retrieved 2026-08-27, License - CC BY-SA 4.0

void MyPopup::showEvent(QShowEvent *event)
{
    QFrame::showEvent(event);

    QRect cursorRect = // ...
    move(cursorRect.bottomLeft());

    QWindow* window = windowHandle();
    window->setProperty("_q_waylandPopupAnchorRect", cursorRect);
    window->setProperty("_q_waylandPopupAnchor", QVariant::fromValue(Qt::BottomEdge | Qt::LeftEdge));
    window->setProperty("_q_waylandPopupGravity", QVariant::fromValue(Qt::BottomEdge | Qt::LeftEdge));
    window->setProperty("_q_waylandPopupConstraintAdjustment", (
        QtWayland::xdg_positioner::constraint_adjustment_slide_x
        | QtWayland::xdg_positioner::constraint_adjustment_flip_x
        | QtWayland::xdg_positioner::constraint_adjustment_flip_y
        | QtWayland::xdg_positioner::constraint_adjustment_resize_x
        | QtWayland::xdg_positioner::constraint_adjustment_resize_y
    ));
}
