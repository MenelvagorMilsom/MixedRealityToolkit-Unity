﻿
using UnityEngine;
using Microsoft.MixedReality.Toolkit.UI;
using Microsoft.MixedReality.Toolkit.Experimental.UI;

namespace Microsoft.MixedReality.Toolkit.Examples.Demos
{
    /// <summary>
    /// Test script that forcefully stops manipulation on the manipulatedObject when it collides with the collisionTrigger
    /// </summary>
    public class ChangeManipulation : MonoBehaviour
    {
        public GameObject manipulatedObject;
        public Collider collisionTrigger;

        private Collider manipulatedObjCollider;

        private void Start()
        {
            if (manipulatedObject != null)
            {
                manipulatedObjCollider = manipulatedObject.GetComponent<Collider>();
            }
        }

        private void Update()
        {
            TryStopManipulation();
        }

        public void TryStopManipulation()
        {
            if (manipulatedObject != null && collisionTrigger != null && manipulatedObjCollider != null)
            {
                if (!collisionTrigger.bounds.Intersects(manipulatedObjCollider.bounds))
                {
                    return;
                }

                var mh = manipulatedObject.GetComponent<ManipulationHandler>();
                var pm = manipulatedObject.GetComponent<PrimitiveManipulator>();
                if (mh != null)
                {
                    mh.ForceEndManipulation();

                    // move the object slightly away from the collision point so we can manipulate it again after this
                    Vector3 direction = collisionTrigger.bounds.center - manipulatedObjCollider.bounds.center;
                    manipulatedObject.transform.Translate(direction.normalized * 0.01f);
                }
                else if (pm != null)
                {
                    pm.ForceEndManipulation();

                    // move the object slightly away from the collision point so we can manipulate it again after this
                    Vector3 direction = collisionTrigger.bounds.center - manipulatedObjCollider.bounds.center;
                    manipulatedObject.transform.Translate(direction.normalized * 0.01f);
                }
            }
        }
    }
}
