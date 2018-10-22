﻿// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License. See LICENSE in the project root for license information.

using Microsoft.MixedReality.Toolkit.Core.Definitions.Utilities;
using Microsoft.MixedReality.Toolkit.Core.Interfaces.Devices;
using Microsoft.MixedReality.Toolkit.Core.Interfaces.InputSystem;
using Microsoft.MixedReality.Toolkit.Core.Managers;
using Microsoft.MixedReality.Toolkit.Core.Utilities;
using System.Collections.Generic;
using UnityEngine;

namespace Microsoft.MixedReality.Toolkit.Core.Devices
{
    /// <summary>
    /// Base Device manager to inherit from.
    /// </summary>
    public class BaseDeviceManager : IMixedRealityDeviceManager
    {
        /// <summary>
        /// Constructor.
        /// </summary>
        /// <param name="name"></param>
        /// <param name="priority"></param>
        public BaseDeviceManager(string name, uint priority)
        {
            Name = name;
            Priority = priority;
        }

        public string Name { get; }

        /// <inheritdoc />
        public uint Priority { get; }

        /// <inheritdoc />
        public virtual void Initialize() { }

        /// <inheritdoc />
        public virtual void Reset() { }

        /// <inheritdoc />
        public virtual void Enable() { }

        /// <inheritdoc />
        public virtual void Update() { }

        /// <inheritdoc />
        public virtual void Disable() { }

        /// <inheritdoc />
        public virtual void Destroy() { }

        /// <inheritdoc />
        public virtual IMixedRealityController[] GetActiveControllers() => new IMixedRealityController[0];

        /// <summary>
        /// Request an array of pointers for the controller type.
        /// </summary>
        /// <param name="controllerType">The controller type making the request for pointers.</param>
        /// <param name="controllingHand">The handedness of the controller making the request.</param>
        /// <param name="useSpecificType">Only register pointers with a specific type.</param>
        /// <returns></returns>
        protected virtual IMixedRealityPointer[] RequestPointers(SystemType controllerType, Handedness controllingHand, bool useSpecificType = false)
        {
            var pointers = new List<IMixedRealityPointer>();

            if (MixedRealityManager.HasActiveProfile &&
                MixedRealityManager.Instance.ActiveProfile.IsInputSystemEnabled &&
                MixedRealityManager.Instance.ActiveProfile.InputSystemProfile.PointerProfile != null)
            {
                for (int i = 0; i < MixedRealityManager.Instance.ActiveProfile.InputSystemProfile.PointerProfile.PointerOptions.Length; i++)
                {
                    var pointerProfile = MixedRealityManager.Instance.ActiveProfile.InputSystemProfile.PointerProfile.PointerOptions[i];

                    if (!useSpecificType)
                    {
                        useSpecificType = pointerProfile.ControllerType.Type != null;
                    }

                    if ((!useSpecificType || pointerProfile.ControllerType.Type == controllerType.Type) &&
                        (pointerProfile.Handedness == Handedness.Any || pointerProfile.Handedness == Handedness.Both || pointerProfile.Handedness == controllingHand))
                    {
                        var pointerObject = Object.Instantiate(pointerProfile.PointerPrefab);
                        var pointer = pointerObject.GetComponent<IMixedRealityPointer>();
                        pointerObject.transform.SetParent(MixedRealityManager.Instance.MixedRealityPlayspace);

                        if (pointer != null)
                        {
                            pointers.Add(pointer);
                        }
                        else
                        {
                            Debug.LogWarning($"Failed to attach {pointerProfile.PointerPrefab.name} to {controllerType.Type.Name}.");
                        }
                    }
                }
            }

            return pointers.Count == 0 ? null : pointers.ToArray();
        }
    }
}